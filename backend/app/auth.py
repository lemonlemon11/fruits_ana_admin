"""密码哈希、服务端会话和权限校验辅助函数。"""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Callable

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from .db import get_db
from .models import (
    AdminAccess,
    AdminLoginLog,
    AdminMenu,
    AdminOperationLog,
    AdminPermission,
    AdminRole,
    AdminRoleMenu,
    AdminRolePermission,
    AdminUserRole,
    User,
    UserSession,
    utc_now,
)


SESSION_COOKIE = os.getenv("FRUIT_ADMIN_SESSION_COOKIE", "fruit_session")
DEFAULT_SESSION_DAYS = 7
REMEMBERED_SESSION_DAYS = 30
ADMIN_PERMISSION_CODES = [
    "admin:dashboard:view",
    "admin:user:view",
    "admin:user:create",
    "admin:user:update",
    "admin:user:delete",
    "admin:user:reset-password",
    "admin:user:disable",
    "admin:role:view",
    "admin:role:create",
    "admin:role:update",
    "admin:role:delete",
    "admin:role:grant",
    "admin:menu:view",
    "admin:menu:create",
    "admin:menu:update",
    "admin:menu:delete",
    "admin:menu:sort",
    "admin:notification:view",
    "admin:notification:create",
    "admin:notification:update",
    "admin:notification:delete",
    "admin:notification:publish",
    "admin:permission:view",
    "admin:permission:create",
    "admin:permission:update",
    "admin:permission:delete",
    "admin:data:view",
    "admin:data:export",
    "admin:data:refresh-cache",
    "admin:log:view",
    "admin:log:export",
    "admin:config:view",
    "admin:config:update",
]
LOGIN_REQUIRED_DETAIL = "请先登录"
FORBIDDEN_DETAIL = "没有权限执行该操作"
PASSWORD_HASHER = PasswordHasher()


def normalize_username(value: str) -> str:
    return value.strip().lower()


def hash_password(password: str) -> str:
    return PASSWORD_HASHER.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return PASSWORD_HASHER.verify(password_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_session(
    db: Session, user: User, session_days: int = DEFAULT_SESSION_DAYS
) -> str:
    raw_token = secrets.token_urlsafe(32)
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=_hash_token(raw_token),
            expires_at=utc_now() + timedelta(days=session_days),
        )
    )
    db.flush()
    return raw_token


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def get_current_user(request: Request, db: Session) -> User | None:
    raw_token = request.cookies.get(SESSION_COOKIE)
    if not raw_token:
        return None

    session = (
        db.query(UserSession)
        .filter(UserSession.token_hash == _hash_token(raw_token))
        .first()
    )
    if session is None:
        return None

    user = session.user if hasattr(session, "user") else db.get(User, session.user_id)
    if user is None or not user.is_active or _as_utc(session.expires_at) <= utc_now():
        db.delete(session)
        db.commit()
        return None
    return user


def require_current_user(
    request: Request, db: Session = Depends(get_db)
) -> User:
    user = get_current_user(request, db)
    if user is None:
        raise HTTPException(status_code=401, detail=LOGIN_REQUIRED_DETAIL)
    return user


def revoke_all_sessions(db: Session, user_id: int) -> None:
    db.query(UserSession).filter(UserSession.user_id == user_id).delete()


def cookie_secure() -> bool:
    return os.getenv("FRUIT_ADMIN_COOKIE_SECURE", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def set_session_cookie(
    response: Response, raw_token: str, session_days: int = DEFAULT_SESSION_DAYS
) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=raw_token,
        max_age=session_days * 86400,
        httponly=True,
        secure=cookie_secure(),
        samesite="lax",
        path="/",
    )


def delete_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE,
        path="/",
        secure=cookie_secure(),
        httponly=True,
        samesite="lax",
    )


def get_role_ids_for_user(db: Session, user_id: int) -> list[int]:
    rows = db.query(AdminUserRole.role_id).filter(AdminUserRole.user_id == user_id).all()
    return [row[0] for row in rows]


def get_roles_for_user(db: Session, user_id: int) -> list[AdminRole]:
    role_ids = get_role_ids_for_user(db, user_id)
    if not role_ids:
        return []
    return db.query(AdminRole).filter(AdminRole.id.in_(role_ids)).all()


def get_admin_access(db: Session, user_id: int) -> AdminAccess | None:
    return (
        db.query(AdminAccess)
        .filter(
            AdminAccess.user_id == user_id,
            AdminAccess.is_active.is_(True),
        )
        .first()
    )


def is_admin_user(db: Session, user_id: int) -> bool:
    return get_admin_access(db, user_id) is not None


def get_permission_codes(db: Session, user_id: int) -> list[str]:
    """管理端权限由控制台访问授权直接给出，与业务 RBAC 分离。"""

    return ADMIN_PERMISSION_CODES.copy() if is_admin_user(db, user_id) else []


def has_permission(db: Session, user_id: int, permission_code: str) -> bool:
    return permission_code in get_permission_codes(db, user_id)


def get_user_menus(db: Session, user_id: int) -> list[AdminMenu]:
    """管理端侧边栏已固定，不再使用业务菜单树。"""

    return []


def require_permission(permission_code: str) -> Callable:
    def dependency(
        request: Request,
        current_user: User = Depends(require_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if not has_permission(db, current_user.id, permission_code):
            raise HTTPException(status_code=403, detail=FORBIDDEN_DETAIL)
        return current_user

    return dependency


def client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def record_login_log(
    db: Session,
    request: Request,
    username: str | None,
    success: bool,
    message: str | None = None,
    user_id: int | None = None,
) -> None:
    db.add(
        AdminLoginLog(
            user_id=user_id,
            username=username,
            success=success,
            message=message,
            ip=client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    )


def record_operation_log(
    db: Session,
    request: Request,
    current_user: User,
    module: str,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    summary: str | None = None,
    before_data: str | None = None,
    after_data: str | None = None,
    status: str = "success",
) -> None:
    db.add(
        AdminOperationLog(
            user_id=current_user.id,
            username=current_user.display_name,
            module=module,
            action=action,
            target_type=target_type,
            target_id=target_id,
            summary=summary,
            before_data=before_data,
            after_data=after_data,
            status=status,
            ip=client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    )
