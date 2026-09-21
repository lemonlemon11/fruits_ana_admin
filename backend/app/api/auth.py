"""管理端登录、当前用户与退出接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import (
    SESSION_COOKIE,
    create_session,
    delete_session_cookie,
    get_current_user,
    get_password_min_length,
    get_permission_codes,
    get_roles_for_user,
    get_session_days,
    get_user_menus,
    hash_password,
    is_admin_user,
    normalize_username,
    record_login_log,
    record_operation_log,
    require_admin_user,
    revoke_all_sessions,
    set_session_cookie,
    verify_password,
)
from ..db import get_db
from ..logging_config import get_logger
from ..models import User, utc_now
from ..schemas import AuthResponse, ChangePasswordRequest, LoginRequest
from ..serializers import menu_tree, role_brief


router = APIRouter(prefix="/api/admin/auth", tags=["admin-auth"])
logger = get_logger()

DISABLED_USER_DETAIL = "该用户已被禁用"


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
    if user is None or not verify_password(
        payload.password, user.password_hash if user else ""
    ):
        logger.warning("login failed reason=invalid_credentials user=%s", payload.display_name)
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

    if not user.is_active:
        logger.warning("login failed reason=disabled user_id=%s", user.id)
        record_login_log(
            db,
            request,
            user.display_name,
            success=False,
            message=DISABLED_USER_DETAIL,
            user_id=user.id,
        )
        db.commit()
        raise HTTPException(status_code=403, detail=DISABLED_USER_DETAIL)

    if not is_admin_user(db, user.id):
        logger.warning("login failed reason=no_admin_permission user_id=%s", user.id)
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
    session_days = get_session_days(db, payload.remember_me)
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
    logger.info("login success user_id=%s remember_me=%s", user.id, payload.remember_me)
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


@router.post("/change-password", status_code=status.HTTP_200_OK)
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    if payload.new_password != payload.confirmation:
        raise HTTPException(status_code=422, detail="两次输入的新密码不一致")
    if not verify_password(payload.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="旧密码不正确")

    min_length = get_password_min_length(db)
    if len(payload.new_password) < min_length:
        raise HTTPException(
            status_code=422,
            detail=f"密码长度不能少于 {min_length} 位",
        )
    if len(payload.new_password) > 128:
        raise HTTPException(status_code=422, detail="密码长度不能超过 128 位")

    current_user.password_hash = hash_password(payload.new_password)
    revoke_all_sessions(db, current_user.id)
    session_days = get_session_days(db, False)
    raw_token = create_session(db, current_user, session_days)
    record_operation_log(
        db,
        request,
        current_user,
        "auth",
        "change-password",
        target_type="user",
        target_id=str(current_user.id),
        summary=f"修改管理端账号 {current_user.display_name} 密码",
    )
    db.commit()
    set_session_cookie(response, raw_token, session_days)
    return {"message": "密码已修改"}
