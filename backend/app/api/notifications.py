"""管理端站内通知管理接口。"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..auth import record_operation_log, require_admin_user
from ..db import get_db
from ..models import (
    AdminNotification,
    AdminNotificationRecipient,
    AdminRole,
    AdminUserRole,
    User,
    utc_now,
)
from ..schemas import (
    NotificationCreate,
    NotificationDetail,
    NotificationListResponse,
    NotificationRead,
    NotificationRecipientRead,
    NotificationUpdate,
)
from ..serializers import notification_read, notification_reads

router = APIRouter(prefix="/api/admin/notifications", tags=["admin-notifications"])
MAX_NOTIFICATION_CONTENT_BYTES = 2 * 1024 * 1024


def _validate_notification_content(content: str | None) -> None:
    if content is None:
        return
    size = len(content.encode("utf-8"))
    if size > MAX_NOTIFICATION_CONTENT_BYTES:
        raise HTTPException(
            status_code=422,
            detail="通知内容不能超过 2MB，请压缩图片或改用外链图片",
        )


def _require_notification(db: Session, notification_id: int) -> AdminNotification:
    notification = db.get(AdminNotification, notification_id)
    if notification is None:
        raise HTTPException(status_code=404, detail="通知不存在")
    return notification


def _json_int_list(value: list[int] | None) -> str | None:
    ids = [int(item) for item in (value or [])]
    return json.dumps(ids, ensure_ascii=False) if ids else None


def _validated_active_user_ids(db: Session, user_ids: list[int]) -> list[int]:
    ids = sorted({int(item) for item in user_ids})
    if not ids:
        raise HTTPException(status_code=422, detail="至少选择一个用户")
    rows = (
        db.query(User.id)
        .filter(User.id.in_(ids), User.is_active.is_(True))
        .all()
    )
    if len(rows) != len(ids):
        raise HTTPException(status_code=422, detail="存在无效或未启用的用户")
    return [row[0] for row in rows]


def _target_user_ids(
    db: Session,
    target_type: str,
    role_ids: list[int] | None,
    user_ids: list[int] | None,
) -> list[int]:
    if target_type == "role":
        role_ids = [int(item) for item in (role_ids or [])]
        if not role_ids:
            raise HTTPException(status_code=422, detail="角色定向通知至少选择一个角色")
        roles = (
            db.query(AdminRole)
            .filter(
                AdminRole.id.in_(role_ids),
                AdminRole.is_active.is_(True),
            )
            .all()
        )
        if len(roles) != len(set(role_ids)):
            raise HTTPException(status_code=422, detail="存在无效或未启用的角色")
        user_ids_by_role = [
            row[0]
            for row in db.query(AdminUserRole.user_id)
            .filter(AdminUserRole.role_id.in_(role_ids))
            .all()
        ]
        if not user_ids_by_role:
            raise HTTPException(status_code=422, detail="所选角色下没有可用用户")
        return _validated_active_user_ids(db, user_ids_by_role)

    if target_type == "user":
        return _validated_active_user_ids(
            db,
            [int(item) for item in (user_ids or [])],
        )

    return [
        row[0]
        for row in db.query(User.id).filter(User.is_active.is_(True)).all()
    ]


def _replace_recipients(
    db: Session, notification: AdminNotification, user_ids: list[int]
) -> None:
    db.query(AdminNotificationRecipient).filter(
        AdminNotificationRecipient.notification_id == notification.id
    ).delete(synchronize_session=False)
    for user_id in user_ids:
        db.add(
            AdminNotificationRecipient(
                notification_id=notification.id,
                user_id=user_id,
            )
        )


def _apply_notification_values(
    notification: AdminNotification, payload: NotificationCreate | NotificationUpdate
) -> None:
    data = payload.model_dump(exclude_unset=True)
    if "content" in data:
        _validate_notification_content(data["content"])
    for key, value in data.items():
        if key in {"target_role_ids", "target_user_ids"}:
            continue
        if key == "is_published" and value is None:
            continue
        if key not in {"publish_at", "expire_at"} and value is None:
            continue
        setattr(notification, key, value)
    if "target_role_ids" in data:
        notification.target_role_ids = _json_int_list(data["target_role_ids"])
    if "target_user_ids" in data:
        notification.target_user_ids = _json_int_list(data["target_user_ids"])


def _is_target_changed(
    notification: AdminNotification,
    payload: NotificationUpdate,
) -> bool:
    data = payload.model_dump(exclude_unset=True)
    if "target_type" in data and data["target_type"] != notification.target_type:
        return True
    if "target_role_ids" in data and _json_int_list(data["target_role_ids"]) != notification.target_role_ids:
        return True
    if "target_user_ids" in data and _json_int_list(data["target_user_ids"]) != notification.target_user_ids:
        return True
    return False


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    notification_type: str | None = None,
    priority: str | None = None,
    is_published: bool | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
):
    query = db.query(AdminNotification)
    if keyword:
        query = query.filter(
            or_(
                AdminNotification.title.ilike(f"%{keyword}%"),
                AdminNotification.content.ilike(f"%{keyword}%"),
            )
        )
    if notification_type:
        query = query.filter(AdminNotification.notification_type == notification_type)
    if priority:
        query = query.filter(AdminNotification.priority == priority)
    if is_published is not None:
        query = query.filter(AdminNotification.is_published.is_(is_published))
    total = query.count()
    items = (
        query.order_by(AdminNotification.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"items": notification_reads(db, items), "total": total}


@router.post("", response_model=NotificationRead, status_code=201)
def create_notification(
    payload: NotificationCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    _validate_notification_content(payload.content)
    user_ids = _target_user_ids(
        db, payload.target_type, payload.target_role_ids, payload.target_user_ids
    )
    publish_at = payload.publish_at
    if payload.is_published and publish_at is None:
        publish_at = utc_now()

    notification = AdminNotification(
        title=payload.title.strip(),
        content=payload.content.strip(),
        notification_type=payload.notification_type,
        priority=payload.priority,
        target_type=payload.target_type,
        target_role_ids=_json_int_list(payload.target_role_ids),
        target_user_ids=_json_int_list(payload.target_user_ids),
        is_published=payload.is_published,
        publish_at=publish_at,
        expire_at=payload.expire_at,
        created_by=current_user.id,
    )
    db.add(notification)
    db.flush()
    if payload.is_published:
        _replace_recipients(db, notification, user_ids)

    record_operation_log(
        db,
        request,
        current_user,
        "notification",
        "create",
        target_type="notification",
        target_id=str(notification.id),
        summary=f"创建通知 {notification.title}",
        after_data=json.dumps(payload.model_dump(), ensure_ascii=False, default=str),
    )
    db.commit()
    return notification_read(db, notification)


@router.get("/{notification_id}", response_model=NotificationDetail)
def get_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
):
    notification = _require_notification(db, notification_id)
    recipients = [
        {"user_id": user.id, "display_name": user.display_name, "is_read": row.is_read, "read_at": row.read_at}
        for row, user in db.query(AdminNotificationRecipient, User)
        .join(User, User.id == AdminNotificationRecipient.user_id)
        .filter(AdminNotificationRecipient.notification_id == notification.id)
        .order_by(User.display_name)
        .all()
    ]
    return {**notification_read(db, notification), "recipients": recipients}


@router.patch("/{notification_id}", response_model=NotificationRead)
def update_notification(
    notification_id: int,
    payload: NotificationUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    notification = _require_notification(db, notification_id)
    target_changed = _is_target_changed(notification, payload)
    if notification.is_published and target_changed:
        raise HTTPException(status_code=400, detail="已发布通知不能修改发送范围")

    was_published = notification.is_published
    _apply_notification_values(notification, payload)

    if target_changed:
        _target_user_ids(
            db,
            notification.target_type,
            [int(item) for item in (json.loads(notification.target_role_ids or "[]") or [])],
            [int(item) for item in (json.loads(notification.target_user_ids or "[]") or [])],
        )

    if payload.is_published and not was_published:
        notification.publish_at = payload.publish_at or utc_now()
        user_ids = _target_user_ids(
            db,
            notification.target_type,
            [int(item) for item in (json.loads(notification.target_role_ids or "[]") or [])],
            [int(item) for item in (json.loads(notification.target_user_ids or "[]") or [])],
        )
        _replace_recipients(db, notification, user_ids)
    elif payload.is_published is False and was_published:
        raise HTTPException(status_code=400, detail="已发布通知不能撤回为草稿")

    record_operation_log(
        db,
        request,
        current_user,
        "notification",
        "update",
        target_type="notification",
        target_id=str(notification.id),
        summary=f"更新通知 {notification.title}",
        after_data=json.dumps(payload.model_dump(), ensure_ascii=False, default=str),
    )
    db.commit()
    return notification_read(db, notification)


@router.post("/{notification_id}/publish", response_model=NotificationRead)
def publish_notification(
    notification_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    notification = _require_notification(db, notification_id)
    if notification.is_published:
        raise HTTPException(status_code=400, detail="通知已发布")
    notification.is_published = True
    notification.publish_at = notification.publish_at or utc_now()
    user_ids = _target_user_ids(
        db,
        notification.target_type,
        [int(item) for item in (json.loads(notification.target_role_ids or "[]") or [])],
        [int(item) for item in (json.loads(notification.target_user_ids or "[]") or [])],
    )
    _replace_recipients(db, notification, user_ids)
    record_operation_log(
        db,
        request,
        current_user,
        "notification",
        "publish",
        target_type="notification",
        target_id=str(notification.id),
        summary=f"发布通知 {notification.title}",
    )
    db.commit()
    return notification_read(db, notification)


@router.delete("/{notification_id}", status_code=204)
def delete_notification(
    notification_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    notification = _require_notification(db, notification_id)
    record_operation_log(
        db,
        request,
        current_user,
        "notification",
        "delete",
        target_type="notification",
        target_id=str(notification.id),
        summary=f"删除通知 {notification.title}",
    )
    db.delete(notification)
    db.commit()
    return None
