"""修复业务系统角色的菜单与权限点授权。

历史版本的角色授权页把管理端 ``admin:*`` 权限混入业务权限树，且「全选」
会把所有权限写入业务角色，导致 ``data_entry``、``registered_user`` 等系统角色
出现种子定义之外的菜单和权限。

本脚本按 ``app.seed.FRUIT_ROLES`` / ``FRUIT_MENUS`` 恢复这些系统角色：

- 系统种子角色：菜单和业务权限都精确恢复为种子定义。
- 非种子角色：只移除 ``admin:*`` 权限，不修改管理员自行配置的业务权限。

幂等，可重复执行；默认只演练，``--apply`` 才写库。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.db import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    AdminMenu,
    AdminPermission,
    AdminRole,
    AdminRoleMenu,
    AdminRolePermission,
)
from app.seed import FRUIT_MENUS, FRUIT_ROLES  # noqa: E402


def _menu_map(db) -> dict[str, AdminMenu]:
    """把种子菜单 key 映射到现有 ``admin_menu`` 记录，不新建记录。"""

    menu_by_key: dict[str, AdminMenu] = {}
    for spec in FRUIT_MENUS:
        parent = menu_by_key.get(spec["parent"]) if spec["parent"] else None
        parent_id = parent.id if parent else None

        item = None
        if spec["permission_code"]:
            item = (
                db.query(AdminMenu)
                .filter(AdminMenu.permission_code == spec["permission_code"])
                .first()
            )
        if item is None and spec["route_path"]:
            item = (
                db.query(AdminMenu)
                .filter(AdminMenu.route_path == spec["route_path"])
                .first()
            )
        if item is None:
            item = (
                db.query(AdminMenu)
                .filter(
                    AdminMenu.parent_id == parent_id,
                    AdminMenu.menu_type == spec["menu_type"],
                    AdminMenu.name == spec["name"],
                )
                .order_by(AdminMenu.sort_order, AdminMenu.id)
                .first()
            )

        if item is not None:
            menu_by_key[spec["key"]] = item
    return menu_by_key


def _permission_map(db) -> dict[str, AdminPermission]:
    return {
        permission.code: permission
        for permission in db.query(AdminPermission).all()
    }


def inspect_plan(db) -> dict:
    """计算每个角色需要新增和删除的菜单/权限 ID。"""

    roles = db.query(AdminRole).order_by(AdminRole.id).all()
    menus = _menu_map(db)
    permissions = _permission_map(db)
    role_specs = {spec["code"]: spec for spec in FRUIT_ROLES}
    admin_permission_ids = {
        permission.id for permission in permissions.values()
        if permission.module == "admin"
    }

    changes = []
    missing_menus = {
        spec["key"] for spec in FRUIT_MENUS if spec["key"] not in menus
    }
    missing_permissions = {
        code
        for spec in FRUIT_ROLES
        for code in spec["permissions"]
        if code not in permissions
    }

    for role in roles:
        current_menu_ids = {
            row[0]
            for row in db.query(AdminRoleMenu.menu_id)
            .filter(AdminRoleMenu.role_id == role.id)
            .all()
        }
        current_permission_ids = {
            row[0]
            for row in db.query(AdminRolePermission.permission_id)
            .filter(AdminRolePermission.role_id == role.id)
            .all()
        }

        spec = role_specs.get(role.code)
        if spec is not None:
            desired_menu_ids = {
                menus[key].id for key in spec["menus"] if key in menus
            }
            desired_permission_ids = {
                permissions[code].id
                for code in spec["permissions"]
                if code in permissions
            }
        else:
            desired_menu_ids = current_menu_ids
            desired_permission_ids = current_permission_ids - admin_permission_ids

        changes.append(
            {
                "role": role,
                "menu_add": sorted(desired_menu_ids - current_menu_ids),
                "menu_remove": sorted(current_menu_ids - desired_menu_ids),
                "permission_add": sorted(
                    desired_permission_ids - current_permission_ids
                ),
                "permission_remove": sorted(
                    current_permission_ids - desired_permission_ids
                ),
            }
        )

    return {
        "changes": changes,
        "missing_menus": missing_menus,
        "missing_permissions": missing_permissions,
    }


def has_work(plan: dict) -> bool:
    return any(
        change["menu_add"]
        or change["menu_remove"]
        or change["permission_add"]
        or change["permission_remove"]
        for change in plan["changes"]
    )


def _summarize(plan: dict) -> None:
    for change in plan["changes"]:
        role = change["role"]
        print(
            f"[角色] id={role.id} code={role.code} "
            f"菜单 -{len(change['menu_remove'])} +{len(change['menu_add'])}；"
            f"权限 -{len(change['permission_remove'])} +{len(change['permission_add'])}"
        )
    if plan["missing_menus"]:
        print(f"[缺失菜单] {sorted(plan['missing_menus'])}")
    if plan["missing_permissions"]:
        print(f"[缺失权限] {sorted(plan['missing_permissions'])}")


def _print_dry_run(plan: dict) -> None:
    for change in plan["changes"]:
        role = change["role"]
        for menu_id in change["menu_remove"]:
            print(f"  [演练] 删除角色 {role.code} 的菜单授权 menu_id={menu_id}")
        for menu_id in change["menu_add"]:
            print(f"  [演练] 新增角色 {role.code} 的菜单授权 menu_id={menu_id}")
        for permission_id in change["permission_remove"]:
            print(
                f"  [演练] 删除角色 {role.code} 的权限授权 permission_id={permission_id}"
            )
        for permission_id in change["permission_add"]:
            print(
                f"  [演练] 新增角色 {role.code} 的权限授权 permission_id={permission_id}"
            )


def _apply(plan: dict) -> None:
    db = SessionLocal()
    try:
        for change in plan["changes"]:
            role = change["role"]
            if change["menu_remove"]:
                db.query(AdminRoleMenu).filter(
                    AdminRoleMenu.role_id == role.id,
                    AdminRoleMenu.menu_id.in_(change["menu_remove"]),
                ).delete(synchronize_session=False)
            for menu_id in change["menu_add"]:
                db.add(AdminRoleMenu(role_id=role.id, menu_id=menu_id))
            if change["permission_remove"]:
                db.query(AdminRolePermission).filter(
                    AdminRolePermission.role_id == role.id,
                    AdminRolePermission.permission_id.in_(
                        change["permission_remove"]
                    ),
                ).delete(synchronize_session=False)
            for permission_id in change["permission_add"]:
                db.add(
                    AdminRolePermission(role_id=role.id, permission_id=permission_id)
                )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def migrate(*, apply: bool = False) -> bool:
    db = SessionLocal()
    try:
        plan = inspect_plan(db)
    finally:
        db.close()

    _summarize(plan)
    if not has_work(plan):
        print("[跳过] 系统角色授权已符合种子定义。")
        return False

    if not apply:
        _print_dry_run(plan)
        return False

    _apply(plan)
    print("[已执行] 系统角色授权修复完成。")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="真正写入数据库；默认只演练")
    args = parser.parse_args(argv)
    migrate(apply=args.apply)
    return 0


if __name__ == "__main__":
    sys.exit(main())
