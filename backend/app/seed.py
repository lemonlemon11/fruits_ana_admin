"""初始化 fruits_ana 业务 RBAC 数据与管理端控制台访问授权。

业务侧数据面向 `fruits_ana` 的菜单和权限；管理端自身权限由
`admin_access` 表单独控制，不在业务菜单/权限管理页面中维护。
"""

from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Session

from .models import (
    AdminAccess,
    AdminMenu,
    AdminPermission,
    AdminRole,
    AdminRoleMenu,
    AdminRolePermission,
    AdminUserRole,
    User,
)

FRUIT_PERMISSIONS: list[tuple[str, str, str, str]] = [
    ("overview:view", "查看销售总览", "overview", "menu"),
    ("settlement:list", "查看结算单列表", "settlement", "menu"),
    ("settlement:detail", "查看结算单详情", "settlement", "menu"),
    ("settlement:comparison", "使用结算单对比", "settlement", "menu"),
    ("series:comparison", "使用品牌系列对比", "series", "menu"),
    ("import:view", "查看数据导入", "import", "menu"),
    ("import:upload", "上传导入文件", "import", "action"),
    ("import:process", "处理导入批次", "import", "action"),
    ("data:export", "导出业务数据", "data", "action"),
    ("ai:refresh", "刷新 AI 分析", "ai", "action"),
    ("preview:view", "查看公开预览", "preview", "menu"),
]

FRUIT_MENUS: list[dict] = [
    {
        "key": "sales-analysis",
        "parent": None,
        "name": "销售分析",
        "menu_type": "directory",
        "route_path": None,
        "component": None,
        "icon": "ChartColumn",
        "permission_code": None,
        "sort_order": 10,
    },
    {
        "key": "overview",
        "parent": "sales-analysis",
        "name": "卖得怎么样",
        "menu_type": "menu",
        "route_path": "/overview",
        "component": "OverviewView",
        "icon": "ChartColumn",
        "permission_code": "overview:view",
        "sort_order": 10,
    },
    {
        "key": "settlements",
        "parent": "sales-analysis",
        "name": "每一单",
        "menu_type": "menu",
        "route_path": "/settlements",
        "component": "SettlementListView",
        "icon": "Table2",
        "permission_code": "settlement:list",
        "sort_order": 20,
    },
    {
        "key": "imports",
        "parent": "sales-analysis",
        "name": "数据导入",
        "menu_type": "menu",
        "route_path": "/imports",
        "component": "ImportView",
        "icon": "Upload",
        "permission_code": "import:view",
        "sort_order": 30,
    },
    {
        "key": "settlement-analysis",
        "parent": None,
        "name": "结算分析",
        "menu_type": "directory",
        "route_path": None,
        "component": None,
        "icon": "PackageSearch",
        "permission_code": None,
        "sort_order": 20,
    },
    {
        "key": "settlement-detail",
        "parent": "settlement-analysis",
        "name": "结算单详情",
        "menu_type": "menu",
        "route_path": "/settlement-detail",
        "component": "SettlementView",
        "icon": "PackageSearch",
        "permission_code": "settlement:detail",
        "sort_order": 10,
    },
    {
        "key": "settlement-comparison",
        "parent": "settlement-analysis",
        "name": "结算单对比",
        "menu_type": "menu",
        "route_path": "/settlement-comparison",
        "component": "SettlementComparisonView",
        "icon": "GitCompareArrows",
        "permission_code": "settlement:comparison",
        "sort_order": 20,
    },
    {
        "key": "series-comparison",
        "parent": "settlement-analysis",
        "name": "品牌对比",
        "menu_type": "menu",
        "route_path": "/series-comparison",
        "component": "SeriesComparisonView",
        "icon": "Boxes",
        "permission_code": "series:comparison",
        "sort_order": 30,
    },
    {
        "key": "preview",
        "parent": None,
        "name": "公开预览",
        "menu_type": "menu",
        "route_path": "/preview",
        "component": "PublicPreviewView",
        "icon": "Eye",
        "permission_code": "preview:view",
        "sort_order": 30,
    },
]

FRUIT_ROLES: list[dict] = [
    {
        "code": "fruit_admin",
        "name": "水果系统管理员",
        "description": "拥有 fruits_ana 全部业务菜单与权限",
        "is_system": True,
        "permissions": [item[0] for item in FRUIT_PERMISSIONS],
        "menus": [item["key"] for item in FRUIT_MENUS],
    },
    {
        "code": "operator",
        "name": "运营人员",
        "description": "查看分析、处理导入并导出业务数据",
        "is_system": True,
        "permissions": [
            "overview:view",
            "settlement:list",
            "settlement:detail",
            "settlement:comparison",
            "series:comparison",
            "import:view",
            "import:upload",
            "import:process",
            "data:export",
            "ai:refresh",
        ],
        "menus": [
            "sales-analysis",
            "overview",
            "settlements",
            "imports",
            "settlement-analysis",
            "settlement-detail",
            "settlement-comparison",
            "series-comparison",
        ],
    },
    {
        "code": "viewer",
        "name": "只读分析员",
        "description": "只读查看 fruits_ana 分析与结算页面",
        "is_system": True,
        "permissions": [
            "overview:view",
            "settlement:list",
            "settlement:detail",
            "settlement:comparison",
            "series:comparison",
            "import:view",
            "preview:view",
        ],
        "menus": [
            "sales-analysis",
            "overview",
            "settlements",
            "imports",
            "settlement-analysis",
            "settlement-detail",
            "settlement-comparison",
            "series-comparison",
            "preview",
        ],
    },
    {
        "code": "data_entry",
        "name": "录单员",
        "description": "负责 fruits_ana 数据导入与录入",
        "is_system": True,
        "permissions": [
            "import:view",
            "import:upload",
            "import:process",
        ],
        "menus": [
            "sales-analysis",
            "imports",
        ],
    },
]

LEGACY_ADMIN_ROLE_CODES = {"super_admin", "operation_admin", "auditor"}


def seed_admin_data(db: Session) -> None:
    """同步 fruits_ana RBAC 数据，并确保控制台账号可登录。"""

    _purge_legacy_admin_rbac(db)
    permission_by_code = _seed_permissions(db)
    menu_by_key = _seed_menus(db)
    _seed_roles(db, permission_by_code, menu_by_key)
    _assign_user_role(db, "test", "fruit_admin")
    _seed_admin_access(db, "test")
    db.commit()


def _purge_legacy_admin_rbac(db: Session) -> None:
    """清理早期误建的管理端自身 RBAC 数据，保留业务 RBAC。"""

    legacy_roles = (
        db.query(AdminRole)
        .filter(AdminRole.code.in_(LEGACY_ADMIN_ROLE_CODES))
        .all()
    )
    for role in legacy_roles:
        db.query(AdminUserRole).filter(AdminUserRole.role_id == role.id).delete()
        db.query(AdminRoleMenu).filter(AdminRoleMenu.role_id == role.id).delete()
        db.query(AdminRolePermission).filter(
            AdminRolePermission.role_id == role.id
        ).delete()
        db.delete(role)

    legacy_permissions = (
        db.query(AdminPermission)
        .filter(AdminPermission.code.like("admin:%"))
        .all()
    )
    legacy_permission_ids = [item.id for item in legacy_permissions]
    if legacy_permission_ids:
        db.query(AdminRolePermission).filter(
            AdminRolePermission.permission_id.in_(legacy_permission_ids)
        ).delete(synchronize_session=False)
        for item in legacy_permissions:
            db.delete(item)

    legacy_menu_components = [
        "DashboardView",
        "UsersView",
        "RolesView",
        "MenusView",
        "PermissionsView",
        "DataView",
        "LogsView",
        "SettingsView",
    ]
    legacy_menus = (
        db.query(AdminMenu)
        .filter(
            or_(
                AdminMenu.route_path.like("/admin/%"),
                AdminMenu.name == "系统管理",
                AdminMenu.component.in_(legacy_menu_components),
            )
        )
        .all()
    )
    legacy_menu_ids = [item.id for item in legacy_menus]
    if legacy_menu_ids:
        db.query(AdminRoleMenu).filter(
            AdminRoleMenu.menu_id.in_(legacy_menu_ids)
        ).delete(synchronize_session=False)
        for item in legacy_menus:
            db.delete(item)
    db.flush()


def _seed_permissions(db: Session) -> dict[str, AdminPermission]:
    result: dict[str, AdminPermission] = {}
    for code, name, module, permission_type in FRUIT_PERMISSIONS:
        item = db.query(AdminPermission).filter(AdminPermission.code == code).first()
        if item is None:
            item = AdminPermission(
                code=code,
                name=name,
                module=module,
                permission_type=permission_type,
            )
            db.add(item)
            db.flush()
        else:
            item.name = name
            item.module = module
            item.permission_type = permission_type
            item.is_active = True
        result[code] = item
    return result


def _seed_menus(db: Session) -> dict[str, AdminMenu]:
    menu_by_key: dict[str, AdminMenu] = {}
    for spec in FRUIT_MENUS:
        parent = menu_by_key.get(spec["parent"]) if spec["parent"] else None
        item = (
            db.query(AdminMenu)
            .filter(
                AdminMenu.name == spec["name"],
                AdminMenu.parent_id == (parent.id if parent else None),
            )
            .first()
        )
        if item is None:
            item = AdminMenu(
                parent_id=parent.id if parent else None,
                name=spec["name"],
                menu_type=spec["menu_type"],
                route_path=spec["route_path"],
                component=spec["component"],
                icon=spec["icon"],
                permission_code=spec["permission_code"],
                sort_order=spec["sort_order"],
            )
            db.add(item)
            db.flush()
        else:
            item.menu_type = spec["menu_type"]
            item.route_path = spec["route_path"]
            item.component = spec["component"]
            item.icon = spec["icon"]
            item.permission_code = spec["permission_code"]
            item.sort_order = spec["sort_order"]
            item.is_active = True
        menu_by_key[spec["key"]] = item
    return menu_by_key


def _seed_roles(
    db: Session,
    permission_by_code: dict[str, AdminPermission],
    menu_by_key: dict[str, AdminMenu],
) -> None:
    for spec in FRUIT_ROLES:
        role = db.query(AdminRole).filter(AdminRole.code == spec["code"]).first()
        if role is None:
            role = AdminRole(
                code=spec["code"],
                name=spec["name"],
                description=spec["description"],
                is_system=spec["is_system"],
            )
            db.add(role)
            db.flush()
        else:
            role.name = spec["name"]
            role.description = spec["description"]
            role.is_system = spec["is_system"]
            role.is_active = True

        db.query(AdminRolePermission).filter(
            AdminRolePermission.role_id == role.id
        ).delete()
        db.query(AdminRoleMenu).filter(AdminRoleMenu.role_id == role.id).delete()
        db.flush()

        for permission_code in spec["permissions"]:
            permission = permission_by_code.get(permission_code)
            if permission is not None:
                db.add(AdminRolePermission(role_id=role.id, permission_id=permission.id))
        for menu_key in spec["menus"]:
            menu = menu_by_key.get(menu_key)
            if menu is not None:
                db.add(AdminRoleMenu(role_id=role.id, menu_id=menu.id))


def _assign_user_role(db: Session, username: str, role_code: str) -> None:
    user = db.query(User).filter(User.display_name == username).first()
    role = db.query(AdminRole).filter(AdminRole.code == role_code).first()
    if user is None or role is None:
        return
    exists = (
        db.query(AdminUserRole)
        .filter(
            AdminUserRole.user_id == user.id,
            AdminUserRole.role_id == role.id,
        )
        .first()
    )
    if exists is None:
        db.add(AdminUserRole(user_id=user.id, role_id=role.id))


def _seed_admin_access(db: Session, username: str) -> None:
    user = db.query(User).filter(User.display_name == username).first()
    if user is None:
        return
    access = (
        db.query(AdminAccess)
        .filter(AdminAccess.user_id == user.id)
        .first()
    )
    if access is None:
        access = AdminAccess(user_id=user.id, is_active=True, is_super_admin=True)
        db.add(access)
    else:
        access.is_active = True
        access.is_super_admin = True
