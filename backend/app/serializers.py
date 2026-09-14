"""模型到响应字典的转换辅助函数。"""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from .auth import get_roles_for_user
from .models import (
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


def role_brief(role: AdminRole) -> dict:
    return {"id": role.id, "code": role.code, "name": role.name}


def permission_brief(permission: AdminPermission) -> dict:
    return {"id": permission.id, "code": permission.code, "name": permission.name}


def user_read(db: Session, user: User) -> dict:
    roles = get_roles_for_user(db, user.id)
    return {
        "id": user.id,
        "display_name": user.display_name,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "roles": [role_brief(role) for role in roles],
    }


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
    user_count = (
        db.query(AdminUserRole)
        .filter(AdminUserRole.role_id == role.id)
        .count()
    )
    menu_ids = [
        row[0]
        for row in db.query(AdminRoleMenu.menu_id)
        .filter(AdminRoleMenu.role_id == role.id)
        .all()
    ]
    permission_ids = [
        row[0]
        for row in db.query(AdminRolePermission.permission_id)
        .filter(AdminRolePermission.role_id == role.id)
        .all()
    ]
    return {
        "id": role.id,
        "code": role.code,
        "name": role.name,
        "description": role.description,
        "is_system": role.is_system,
        "is_active": role.is_active,
        "user_count": user_count,
        "menu_ids": menu_ids,
        "permission_ids": permission_ids,
    }


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
    recipient_total = (
        db.query(AdminNotificationRecipient)
        .filter(AdminNotificationRecipient.notification_id == notification.id)
        .count()
    )
    read_count = (
        db.query(AdminNotificationRecipient)
        .filter(
            AdminNotificationRecipient.notification_id == notification.id,
            AdminNotificationRecipient.is_read.is_(True),
        )
        .count()
    )
    return {
        "id": notification.id,
        "title": notification.title,
        "content": notification.content,
        "notification_type": notification.notification_type,
        "priority": notification.priority,
        "target_type": notification.target_type,
        "target_role_ids": _int_list(notification.target_role_ids),
        "target_user_ids": _int_list(notification.target_user_ids),
        "is_published": notification.is_published,
        "publish_at": notification.publish_at,
        "expire_at": notification.expire_at,
        "created_by": notification.created_by,
        "created_at": notification.created_at,
        "updated_at": notification.updated_at,
        "recipient_total": recipient_total,
        "read_count": read_count,
        "unread_count": recipient_total - read_count,
    }
