"""初始化 fruits_ana 业务 RBAC 数据与唯一管理端账号。

业务角色 / 菜单 / 权限点只负责用户端权限；管理端不再维护控制台权限点。
应用启动时会幂等创建唯一管理端账号 ``admin``。
"""

from __future__ import annotations

import os

from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .auth import hash_password
from .models import (
    AdminAccess,
    AdminMenu,
    AdminPermission,
    AdminRole,
    AdminRoleMenu,
    AdminRolePermission,
    EntryFieldOption,
    FieldConversionRule,
    User,
)

ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = os.getenv("FRUIT_ADMIN_DEFAULT_PASSWORD", "12345678")

FRUIT_PERMISSIONS: list[tuple[str, str, str, str]] = [
    ("overview:view", "查看销售总览", "overview", "menu"),
    ("settlement:list", "查看结算单列表", "settlement", "menu"),
    ("settlement:detail", "查看结算单详情", "settlement", "menu"),
    ("settlement:comparison", "使用结算单对比", "settlement", "menu"),
    ("series:comparison", "使用品牌系列对比", "series", "menu"),
    ("import:view", "查看录单 / 导入", "import", "menu"),
    ("import:upload", "上传导入文件", "import", "action"),
    ("import:process", "处理导入批次", "import", "action"),
    ("entry:view", "查看手工录单页面", "import", "action"),
    ("entry:create", "新增手工录单", "import", "action"),
    ("entry:update", "修改手工录单", "import", "action"),
    ("entry:export", "导出手工录单", "import", "action"),
    ("data:export", "导出业务数据", "data", "action"),
    ("ai:refresh", "刷新 AI 分析", "ai", "action"),
    ("ask:view", "使用数据问答顺仔", "ask", "action"),
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
        "name": "录单 / 导入",
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
]

FRUIT_ROLES: list[dict] = [
    {
        "code": "registered_user",
        "name": "新注册用户",
        "description": "新用户注册后的默认角色，暂不开放任何菜单和权限",
        "is_system": True,
        "permissions": [],
        "menus": [],
    },
    {
        "code": "fruit_admin",
        "name": "业务主管理员",
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
            "entry:view",
            "entry:create",
            "entry:update",
            "entry:export",
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
        "code": "data_entry",
        "name": "录单员",
        "description": "负责 fruits_ana 数据导入与录入",
        "is_system": True,
        "permissions": [
            "import:view",
            "import:upload",
            "import:process",
            "entry:view",
            "entry:create",
            "entry:update",
            "entry:export",
        ],
        "menus": [
            "sales-analysis",
            "imports",
        ],
    },
]

def seed_admin_data(db: Session) -> None:
    """补缺唯一管理端账号、业务权限/菜单/角色及基础配置。"""

    permission_by_code = _seed_permission_specs(db, FRUIT_PERMISSIONS)
    menu_by_key = _seed_menus(db)
    _seed_roles(db, permission_by_code, menu_by_key)
    _seed_admin_account(db)
    _remove_admin_permissions(db)
    _seed_field_conversion_rules(db)
    db.commit()

    try:
        _seed_entry_field_options(db)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        print(
            "[seed] 跳过录单字段字典种子：共享表 entry_field_option 尚不可用，"
            "请先启动 fruits_ana 用户端初始化共享表。"
            f"（{exc}）"
        )


def _seed_admin_account(db: Session) -> None:
    """创建唯一管理端账号 admin，并确保其他账号没有控制台访问授权。"""

    user = db.query(User).filter(User.display_name == ADMIN_USERNAME).first()
    if user is None:
        user = User(
            display_name=ADMIN_USERNAME,
            password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
            is_active=True,
        )
        db.add(user)
        db.flush()

    db.query(AdminAccess).filter(AdminAccess.user_id != user.id).delete(
        synchronize_session=False
    )
    access = db.query(AdminAccess).filter(AdminAccess.user_id == user.id).first()
    if access is None:
        db.add(
            AdminAccess(
                user_id=user.id,
                is_active=True,
                is_super_admin=True,
            )
        )
    else:
        access.is_active = True
        access.is_super_admin = True


def _remove_admin_permissions(db: Session) -> None:
    """删除历史遗留的管理端 ``admin:*`` 权限点及其角色引用。"""

    admin_permissions = (
        db.query(AdminPermission)
        .filter(AdminPermission.module == "admin")
        .all()
    )
    if not admin_permissions:
        return

    permission_ids = [permission.id for permission in admin_permissions]
    db.query(AdminRolePermission).filter(
        AdminRolePermission.permission_id.in_(permission_ids)
    ).delete(synchronize_session=False)
    for permission in admin_permissions:
        db.delete(permission)


def _seed_permission_specs(
    db: Session,
    specs: list[tuple[str, str, str, str]],
) -> dict[str, AdminPermission]:
    result: dict[str, AdminPermission] = {}
    for code, name, module, permission_type in specs:
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
        result[code] = item
    return result


def _find_seed_menu(
    db: Session, spec: dict, parent_id: int | None
) -> AdminMenu | None:
    """按稳定标识查找种子菜单，避免管理员改名后被重复补建。

    匹配优先级：权限码 → 路由路径 → 同级同类排序 → 同级同类同名。
    前两项与界面文案无关，管理员重命名菜单后仍能命中同一条记录；
    后两项为没有权限码与路由的目录兜底。
    """

    for column, value in (
        (AdminMenu.permission_code, spec["permission_code"]),
        (AdminMenu.route_path, spec["route_path"]),
    ):
        if not value:
            continue
        item = db.query(AdminMenu).filter(column == value).first()
        if item is not None:
            return item

    return (
        db.query(AdminMenu)
        .filter(
            AdminMenu.parent_id == parent_id,
            AdminMenu.menu_type == spec["menu_type"],
            or_(
                AdminMenu.sort_order == spec["sort_order"],
                AdminMenu.name == spec["name"],
            ),
        )
        .order_by(AdminMenu.sort_order, AdminMenu.id)
        .first()
    )


def _seed_menus(db: Session) -> dict[str, AdminMenu]:
    menu_by_key: dict[str, AdminMenu] = {}
    for spec in FRUIT_MENUS:
        parent = menu_by_key.get(spec["parent"]) if spec["parent"] else None
        parent_id = parent.id if parent else None
        item = _find_seed_menu(db, spec, parent_id)
        if item is None:
            item = AdminMenu(
                parent_id=parent_id,
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
            for permission_code in spec["permissions"]:
                permission = permission_by_code.get(permission_code)
                if permission is not None:
                    db.add(
                        AdminRolePermission(
                            role_id=role.id,
                            permission_id=permission.id,
                        )
                    )
            for menu_key in spec["menus"]:
                menu = menu_by_key.get(menu_key)
                if menu is not None:
                    db.add(AdminRoleMenu(role_id=role.id, menu_id=menu.id))
        elif role.is_system and role.name != spec["name"]:
            role.name = spec["name"]


def _seed_entry_field_options(db: Session) -> None:
    """预置品种 A-F；市场不预置，由 fruit_admin 自行维护。"""

    for order, value in enumerate("ABCDEF"):
        option = (
            db.query(EntryFieldOption)
            .filter(
                EntryFieldOption.field_key == "variety",
                EntryFieldOption.value == value,
            )
            .first()
        )
        if option is None:
            db.add(
                EntryFieldOption(
                    field_key="variety",
                    value=value,
                    sort_order=order,
                    is_active=True,
                )
            )


def _seed_field_conversion_rules(db: Session) -> None:
    """预置默认品种转换规则：BC 展示原文，统计归 C。"""

    rule = (
        db.query(FieldConversionRule)
        .filter(
            FieldConversionRule.field_key == "grade",
            FieldConversionRule.source_value == "BC",
        )
        .first()
    )
    if rule is None:
        db.add(
            FieldConversionRule(
                field_key="grade",
                source_value="BC",
                target_value="C",
                sort_order=0,
                is_active=True,
                description="BC 界面显示原文，统计统一归入 C",
            )
        )
