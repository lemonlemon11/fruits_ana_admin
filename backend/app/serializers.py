"""模型到响应字典的转换辅助函数。"""

from __future__ import annotations

import json
from collections import defaultdict

from zoneinfo import ZoneInfo
from datetime import timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from .auth import get_roles_for_user
from .models import (
    as_beijing_str,
    AdminMenu,
    AdminNotification,
    AdminNotificationRecipient,
    AdminPermission,
    AdminRole,
    AdminRoleMenu,
    AdminRolePermission,
    AdminUserRole,
    User,
)


BEIJING_TZ = ZoneInfo("Asia/Shanghai")


def _as_beijing(dt):
    """Convert UTC datetime (naive treated as UTC) to Beijing timezone-aware datetime."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(BEIJING_TZ)


def role_brief(role: AdminRole) -> dict:
    return {"id": role.id, "code": role.code, "name": role.name}


def permission_brief(permission: AdminPermission) -> dict:
    return {"id": permission.id, "code": permission.code, "name": permission.name}


def user_read(db: Session, user: User) -> dict:
    roles = get_roles_for_user(db, user.id)
    return {
        "id": user.id,
        "display_name": user.display_name,
        "email": user.email,
        "is_active": user.is_active,
        "created_at": as_beijing_str(user.created_at),
        "last_login_at": as_beijing_str(user.last_login_at),
        "roles": [role_brief(role) for role in roles],
    }


def user_reads(db: Session, users: list[User]) -> list[dict]:
    """批量读取用户角色，避免列表页每行查询一次角色。"""

    if not users:
        return []

    user_ids = [user.id for user in users]
    role_rows = (
        db.query(AdminUserRole.user_id, AdminUserRole.role_id)
        .filter(AdminUserRole.user_id.in_(user_ids))
        .all()
    )
    role_ids = sorted({role_id for _, role_id in role_rows})
    roles_by_id = {
        role.id: role
        for role in db.query(AdminRole).filter(AdminRole.id.in_(role_ids)).all()
    } if role_ids else {}
    roles_by_user: dict[int, list[AdminRole]] = defaultdict(list)
    for user_id, role_id in role_rows:
        role = roles_by_id.get(role_id)
        if role is not None:
            roles_by_user[user_id].append(role)

    return [
        {
            "id": user.id,
            "display_name": user.display_name,
            "email": user.email,
            "is_active": user.is_active,
            "created_at": as_beijing_str(user.created_at),
            "last_login_at": as_beijing_str(user.last_login_at),
            "roles": [role_brief(role) for role in roles_by_user[user.id]],
        }
        for user in users
    ]


def menu_read(menu: AdminMenu) -> dict:
    return {
        "id": menu.id,
        "parent_id": menu.parent_id,
        "name": menu.name,
        "menu_type": menu.menu_type,
        "route_path": menu.route_path,
        "component": menu.component,
        "icon": menu.icon,
        "permission_code": menu.permission_code,
        "sort_order": menu.sort_order,
        "is_active": menu.is_active,
    }


def menu_tree(menus: list[AdminMenu]) -> list[dict]:
    nodes = [menu_read(menu) | {"children": []} for menu in menus]
    by_id = {node["id"]: node for node in nodes}
    roots: list[dict] = []
    for node in nodes:
        if node["parent_id"] is not None and node["parent_id"] in by_id:
            by_id[node["parent_id"]]["children"].append(node)
        else:
            roots.append(node)
    return roots


def role_read(db: Session, role: AdminRole) -> dict:
    return role_reads(db, [role])[0]


def role_reads(db: Session, roles: list[AdminRole]) -> list[dict]:
    """批量读取角色统计与授权项，避免列表页 N+1。"""

    if not roles:
        return []

    role_ids = [role.id for role in roles]
    user_count_rows = (
        db.query(AdminUserRole.role_id, func.count(AdminUserRole.id))
        .filter(AdminUserRole.role_id.in_(role_ids))
        .group_by(AdminUserRole.role_id)
        .all()
    )
    user_counts = {role_id: count for role_id, count in user_count_rows}

    menu_rows = (
        db.query(AdminRoleMenu.role_id, AdminRoleMenu.menu_id)
        .filter(AdminRoleMenu.role_id.in_(role_ids))
        .all()
    )
    # 角色授权页只管理用户端业务权限，管理端不再维护控制台权限点。
    permission_rows = (
        db.query(AdminRolePermission.role_id, AdminRolePermission.permission_id)
        .join(
            AdminPermission,
            AdminPermission.id == AdminRolePermission.permission_id,
        )
        .filter(
            AdminRolePermission.role_id.in_(role_ids),
            AdminPermission.module != "admin",
        )
        .all()
    )
    menus_by_role: dict[int, list[int]] = defaultdict(list)
    permissions_by_role: dict[int, list[int]] = defaultdict(list)
    for role_id, menu_id in menu_rows:
        menus_by_role[role_id].append(menu_id)
    for role_id, permission_id in permission_rows:
        permissions_by_role[role_id].append(permission_id)

    return [
        {
            "id": role.id,
            "code": role.code,
            "name": role.name,
            "description": role.description,
            "is_system": role.is_system,
            "is_active": role.is_active,
            "user_count": user_counts.get(role.id, 0),
            "menu_ids": menus_by_role[role.id],
            "permission_ids": permissions_by_role[role.id],
        }
        for role in roles
    ]


def permission_read(permission: AdminPermission) -> dict:
    return {
        "id": permission.id,
        "code": permission.code,
        "name": permission.name,
        "module": permission.module,
        "permission_type": permission.permission_type,
        "description": permission.description,
        "is_active": permission.is_active,
    }


def _int_list(value: str | None) -> list[int]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return []
    return [int(item) for item in parsed if str(item).isdigit()] if isinstance(parsed, list) else []


def notification_read(db: Session, notification: AdminNotification) -> dict:
    return notification_reads(db, [notification])[0]


def notification_reads(
    db: Session, notifications: list[AdminNotification]
) -> list[dict]:
    """批量读取通知阅读统计，避免列表页每行两次查询。"""

    if not notifications:
        return []

    notification_ids = [notification.id for notification in notifications]
    total_rows = (
        db.query(
            AdminNotificationRecipient.notification_id,
            func.count(AdminNotificationRecipient.id),
        )
        .filter(AdminNotificationRecipient.notification_id.in_(notification_ids))
        .group_by(AdminNotificationRecipient.notification_id)
        .all()
    )
    read_rows = (
        db.query(
            AdminNotificationRecipient.notification_id,
            func.count(AdminNotificationRecipient.id),
        )
        .filter(
            AdminNotificationRecipient.notification_id.in_(notification_ids),
            AdminNotificationRecipient.is_read.is_(True),
        )
        .group_by(AdminNotificationRecipient.notification_id)
        .all()
    )
    totals = {notification_id: count for notification_id, count in total_rows}
    reads = {notification_id: count for notification_id, count in read_rows}

    result = []
    for notification in notifications:
        recipient_total = totals.get(notification.id, 0)
        read_count = reads.get(notification.id, 0)
        result.append({
            "id": notification.id,
            "title": notification.title,
            "content": notification.content,
            "notification_type": notification.notification_type,
            "priority": notification.priority,
            "target_type": notification.target_type,
            "target_role_ids": _int_list(notification.target_role_ids),
            "target_user_ids": _int_list(notification.target_user_ids),
            "is_published": notification.is_published,
            "publish_at": _as_beijing(notification.publish_at),
            "expire_at": _as_beijing(notification.expire_at),
            "created_by": notification.created_by,
            "created_at": _as_beijing(notification.created_at),
            "updated_at": _as_beijing(notification.updated_at),
            "recipient_total": recipient_total,
            "read_count": read_count,
            "unread_count": recipient_total - read_count,
        })
    return result
