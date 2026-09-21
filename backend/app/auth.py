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
    AdminSetting,
    AdminUserRole,
    User,
    UserSession,
    utc_now,
)


SESSION_COOKIE = os.getenv("FRUIT_ADMIN_SESSION_COOKIE", "fruit_admin_session")
if SESSION_COOKIE in {"", "fruit_session"}:
    SESSION_COOKIE = "fruit_admin_session"
DEFAULT_SESSION_DAYS = 7
REMEMBERED_SESSION_DAYS = 30
LOGIN_REQUIRED_DETAIL = "请先登录"
PASSWORD_HASHER = PasswordHasher()


def normalize_username(value: str) -> str:
    return value.strip().lower()


def get_setting_value(db: Session, key: str, default: str | None = None) -> str | None:
    item = db.query(AdminSetting).filter(AdminSetting.key == key).first()
    if item is None or item.value is None:
        return default
    return item.value


def get_setting_int(db: Session, key: str, default: int) -> int:
    try:
        return int(get_setting_value(db, key, str(default)))
    except (TypeError, ValueError):
        return default


def get_session_days(db: Session, remember_me: bool = False) -> int:
    key = "remember_days" if remember_me else "session_days"
    default = REMEMBERED_SESSION_DAYS if remember_me else DEFAULT_SESSION_DAYS
    return max(1, get_setting_int(db, key, default))


def get_password_min_length(db: Session) -> int:
    return min(128, max(1, get_setting_int(db, "password_min_length", 8)))


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
    """返回用户持有的业务端权限码，管理端不再使用 ``admin:*`` 权限点。"""

    role_ids = get_role_ids_for_user(db, user_id)
    if not role_ids:
        return []

    rows = (
        db.query(AdminPermission.code)
        .join(
            AdminRolePermission,
            AdminRolePermission.permission_id == AdminPermission.id,
        )
        .join(AdminRole, AdminRole.id == AdminRolePermission.role_id)
        .filter(
            AdminRole.id.in_(role_ids),
            AdminRole.is_active.is_(True),
            AdminPermission.is_active.is_(True),
            AdminPermission.module != "admin",
        )
        .distinct()
        .all()
    )
    return [row[0] for row in rows]


def get_user_menus(db: Session, user_id: int) -> list[AdminMenu]:
    """管理端侧边栏已固定，不再使用业务菜单树。"""

    return []


def require_admin_user(
    request: Request,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
) -> User:
    """要求当前请求来自唯一的内置管理端账号。"""

    if not is_admin_user(db, current_user.id):
        raise HTTPException(status_code=403, detail="该账号没有管理端访问权限")
    return current_user


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
