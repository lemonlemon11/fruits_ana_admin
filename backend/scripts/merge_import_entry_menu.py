"""合并管理端「数据导入」与「手工录单」为「录单 / 导入」。

``fruits_ana`` 用户端已把两条录入入口合成一个侧栏菜单：``/entry`` 由导入页
页头进入，``/entry-hub`` 重定向到 ``/imports``。管理端菜单树与授权树需要同步
清理，否则会残留两个已失效的平级菜单。

迁移动作（幂等，可重复执行；菜单按 ``route_path`` 定位，不依赖自增 ID）：

1. 把 ``admin_role_menu`` 中指向「手工录单」的角色授权改指「数据导入」；
   若该角色已同时授权两者，则删除重复行（保留唯一约束 ``ux_admin_role_menu``）。
2. 删除「手工录单」菜单。
3. 把「数据导入」重命名为「录单 / 导入」。
4. 同步权限点：``import:view`` 改名；``entry:*`` 的 ``module`` 由 ``entry``
   改为 ``import``（授权树按 ``module`` 归组），``entry:view`` 改成 action 类型。
   权限编码 ``entry:*`` 不变——``fruits_ana`` 的 ``/entry`` 路由仍按它鉴权。

默认只演练，``--apply`` 才写库。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import text

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.db import engine  # noqa: E402


TARGET_ROUTE = "/imports"
SOURCE_ROUTE = "/entry"
TARGET_NAME = "录单 / 导入"

# (权限编码, 新名称, 新 module, 新 permission_type)
PERMISSION_UPDATES: list[tuple[str, str, str, str]] = [
    ("import:view", "查看录单 / 导入", "import", "menu"),
    ("entry:view", "查看手工录单页面", "import", "action"),
    ("entry:create", "新增手工录单", "import", "action"),
    ("entry:update", "修改手工录单", "import", "action"),
    ("entry:export", "导出手工录单", "import", "action"),
]


def _load_menu(connection, route_path: str):
    return connection.execute(
        text(
            "SELECT id, name, route_path FROM admin_menu "
            "WHERE route_path = :route_path ORDER BY id LIMIT 1"
        ),
        {"route_path": route_path},
    ).first()


def _permission_drift(connection) -> list[dict]:
    """返回字段确有差异的权限点，避免无意义的 UPDATE。"""

    changes: list[dict] = []
    for code, name, module, permission_type in PERMISSION_UPDATES:
        row = connection.execute(
            text(
                "SELECT id, code, name, module, permission_type "
                "FROM admin_permission WHERE code = :code"
            ),
            {"code": code},
        ).first()
        if row is None:
            continue
        if (row.name, row.module, row.permission_type) == (name, module, permission_type):
            continue
        changes.append(
            {
                "id": row.id,
                "code": row.code,
                "name": name,
                "module": module,
                "permission_type": permission_type,
                "before": f"{row.name} / {row.module} / {row.permission_type}",
            }
        )
    return changes


def _role_menu_drift(connection, target, source) -> tuple[list, list]:
    """返回（需改指目标菜单的授权行, 重复需删除的授权行）。"""

    if target is None or source is None:
        return [], []

    source_rows = connection.execute(
        text(
            "SELECT id, role_id FROM admin_role_menu "
            "WHERE menu_id = :menu_id ORDER BY role_id"
        ),
        {"menu_id": source.id},
    ).fetchall()
    target_role_ids = {
        row.role_id
        for row in connection.execute(
            text("SELECT role_id FROM admin_role_menu WHERE menu_id = :menu_id"),
            {"menu_id": target.id},
        ).fetchall()
    }
    moved = [row for row in source_rows if row.role_id not in target_role_ids]
    duplicated = [row for row in source_rows if row.role_id in target_role_ids]
    return moved, duplicated


def inspect_plan() -> dict:
    """收集菜单与权限的待迁移项，供演练与执行共用。"""

    with engine.connect() as connection:
        target = _load_menu(connection, TARGET_ROUTE)
        source = _load_menu(connection, SOURCE_ROUTE)
        move_rows, drop_rows = _role_menu_drift(connection, target, source)
        permissions = _permission_drift(connection)

    return {
        "target": target,
        "source": source,
        "needs_rename": target is not None and target.name != TARGET_NAME,
        "move_rows": move_rows,
        "drop_rows": drop_rows,
        "permissions": permissions,
    }


def _summarize(plan: dict) -> None:
    target, source = plan["target"], plan["source"]
    if source is None:
        print(f"[跳过] 未找到 route_path={SOURCE_ROUTE} 的菜单，菜单已合并。")
    else:
        print(f"[目标菜单] id={target.id} name={target.name} route={target.route_path}")
        print(f"[合并菜单] id={source.id} name={source.name} route={source.route_path}")
        print(
            f"[菜单授权] 迁移 {len(plan['move_rows'])} 条，"
            f"删除重复 {len(plan['drop_rows'])} 条"
        )
    rename_state = (
        f"需要重命名为「{TARGET_NAME}」" if plan["needs_rename"] else f"已是「{TARGET_NAME}」"
    )
    print(f"[菜单名称] {rename_state}")
    print(f"[权限点] 需要更新 {len(plan['permissions'])} 条")


def _print_dry_run(plan: dict) -> None:
    target, source = plan["target"], plan["source"]
    for row in plan["move_rows"]:
        print(f"  [演练] admin_role_menu id={row.id} menu_id {source.id} → {target.id}")
    for row in plan["drop_rows"]:
        print(f"  [演练] 删除重复 admin_role_menu id={row.id}（角色 {row.role_id} 已含目标菜单）")
    if source is not None:
        print(f"  [演练] 删除菜单 id={source.id}（{source.name}）")
    if plan["needs_rename"]:
        print(f"  [演练] 菜单 id={target.id}「{target.name}」重命名为「{TARGET_NAME}」")
    for row in plan["permissions"]:
        print(
            f"  [演练] 权限 {row['code']}：{row['before']} → "
            f"{row['name']} / {row['module']} / {row['permission_type']}"
        )
    if source is None and not plan["permissions"] and not plan["needs_rename"]:
        print("[演练] 无待迁移项，已是最新状态。")


def _apply_plan(plan: dict) -> None:
    target, source = plan["target"], plan["source"]
    with engine.begin() as connection:
        for row in plan["move_rows"]:
            connection.execute(
                text("UPDATE admin_role_menu SET menu_id = :menu_id WHERE id = :id"),
                {"menu_id": target.id, "id": row.id},
            )
        for row in plan["drop_rows"]:
            connection.execute(
                text("DELETE FROM admin_role_menu WHERE id = :id"), {"id": row.id}
            )
        if source is not None:
            connection.execute(
                text("DELETE FROM admin_menu WHERE id = :id"), {"id": source.id}
            )
        if plan["needs_rename"]:
            connection.execute(
                text("UPDATE admin_menu SET name = :name WHERE id = :id"),
                {"name": TARGET_NAME, "id": target.id},
            )
        for row in plan["permissions"]:
            connection.execute(
                text(
                    "UPDATE admin_permission SET name = :name, module = :module, "
                    "permission_type = :permission_type WHERE id = :id"
                ),
                {
                    "name": row["name"],
                    "module": row["module"],
                    "permission_type": row["permission_type"],
                    "id": row["id"],
                },
            )


def _has_work(plan: dict) -> bool:
    return bool(
        plan["source"] is not None
        or plan["needs_rename"]
        or plan["move_rows"]
        or plan["drop_rows"]
        or plan["permissions"]
    )


def migrate(*, apply: bool = False) -> bool:
    plan = inspect_plan()
    if plan["target"] is None:
        print(f"[跳过] 未找到 route_path={TARGET_ROUTE} 的菜单，可能尚未初始化。")
        return False

    _summarize(plan)
    if not _has_work(plan):
        print("[跳过] 无待迁移项，已是最新状态。")
        return False

    if not apply:
        _print_dry_run(plan)
        return False

    _apply_plan(plan)
    print(f"[已执行] 菜单与权限合并完成：{TARGET_NAME}")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="真正写入数据库；默认只演练")
    args = parser.parse_args(argv)
    migrate(apply=args.apply)
    return 0


if __name__ == "__main__":
    sys.exit(main())
