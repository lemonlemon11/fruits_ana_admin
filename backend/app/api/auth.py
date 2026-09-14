"""管理端登录、当前用户与退出接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import (
    DEFAULT_SESSION_DAYS,
    REMEMBERED_SESSION_DAYS,
    SESSION_COOKIE,
    create_session,
    delete_session_cookie,
    get_current_user,
    get_permission_codes,
    get_roles_for_user,
    get_user_menus,
    is_admin_user,
    normalize_username,
    record_login_log,
    set_session_cookie,
    verify_password,
)
from ..db import get_db
from ..models import User, utc_now
from ..schemas import AuthResponse, LoginRequest
from ..serializers import menu_tree, role_brief


router = APIRouter(prefix="/api/admin/auth", tags=["admin-auth"])


def _find_user_by_name(db: Session, display_name: str) -> User | None:
    normalized = normalize_username(display_name)
    return (
        db.query(User)
        .filter(func.lower(User.display_name) == normalized)
        .first()
    )


def _auth_payload(db: Session, user: User) -> dict:
    menus = get_user_menus(db, user.id)
    return {
        "user": {
            "id": user.id,
            "display_name": user.display_name,
            "is_active": user.is_active,
            "roles": [role_brief(role) for role in get_roles_for_user(db, user.id)],
            "permissions": get_permission_codes(db, user.id),
            "menus": menu_tree(menus),
        }
    }


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    user = _find_user_by_name(db, payload.display_name)
    if user is None or not user.is_active or not verify_password(
        payload.password, user.password_hash if user else ""
    ):
        record_login_log(
            db,
            request,
            payload.display_name,
            success=False,
            message="用户名或密码错误",
            user_id=user.id if user else None,
        )
        db.commit()
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    if not is_admin_user(db, user.id):
        record_login_log(
            db,
            request,
            user.display_name,
            success=False,
            message="该账号没有管理端访问权限",
            user_id=user.id,
        )
        db.commit()
        raise HTTPException(status_code=403, detail="该账号没有管理端访问权限")

    user.last_login_at = utc_now()
    session_days = (
        REMEMBERED_SESSION_DAYS if payload.remember_me else DEFAULT_SESSION_DAYS
    )
    raw_token = create_session(db, user, session_days)
    record_login_log(
        db,
        request,
        user.display_name,
        success=True,
        message="登录成功",
        user_id=user.id,
    )
    db.commit()
    set_session_cookie(response, raw_token, session_days)
    return _auth_payload(db, user)


@router.get("/me", response_model=AuthResponse)
def me(
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if user is None:
        raise HTTPException(status_code=401, detail="请先登录")
    if not is_admin_user(db, user.id):
        raise HTTPException(status_code=403, detail="该账号没有管理端访问权限")
    return _auth_payload(db, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    raw_token = request.cookies.get(SESSION_COOKIE)
    if raw_token:
        from ..models import UserSession
        from ..auth import _hash_token

        session = (
            db.query(UserSession)
            .filter(UserSession.token_hash == _hash_token(raw_token))
            .first()
        )
        if session:
            db.delete(session)
            db.commit()
    delete_session_cookie(response)
    return None
