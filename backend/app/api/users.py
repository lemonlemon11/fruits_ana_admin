"""管理端用户管理接口。"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..auth import (
    get_password_min_length,
    hash_password,
    normalize_username,
    record_operation_log,
    require_current_user,
    require_admin_user,
    revoke_all_sessions,
)
from ..db import get_db
from ..models import AdminRole, AdminUserRole, User
from ..schemas import ResetPasswordRequest, UserCreate, UserListResponse, UserUpdate
from ..serializers import user_read, user_reads


router = APIRouter(prefix="/api/admin/users", tags=["admin-users"])


def _require_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


def _require_roles(db: Session, role_ids: list[int]) -> list[AdminRole]:
    roles = db.query(AdminRole).filter(AdminRole.id.in_(role_ids)).all() if role_ids else []
    if len(roles) != len(set(role_ids)):
        raise HTTPException(status_code=422, detail="存在无效角色")
    return roles


def _replace_user_roles(db: Session, user_id: int, role_ids: list[int]) -> None:
    db.query(AdminUserRole).filter(AdminUserRole.user_id == user_id).delete()
    for role_id in role_ids:
        db.add(AdminUserRole(user_id=user_id, role_id=role_id))


def _find_user_by_name(db: Session, display_name: str) -> User | None:
    normalized = normalize_username(display_name)
    return (
        db.query(User)
        .filter(func.lower(User.display_name) == normalized)
        .first()
    )


def _validate_password_length(db: Session, password: str) -> None:
    min_length = get_password_min_length(db)
    if len(password) < min_length:
        raise HTTPException(
            status_code=422,
            detail=f"密码长度不能少于 {min_length} 位",
        )


@router.get("", response_model=UserListResponse)
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    is_active: bool | None = None,
    role_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
):
    query = db.query(User)
    if keyword:
        query = query.filter(User.display_name.ilike(f"%{keyword}%"))
    if is_active is not None:
        query = query.filter(User.is_active.is_(is_active))
    if role_id is not None:
        user_ids = [
            row[0]
            for row in db.query(AdminUserRole.user_id)
            .filter(AdminUserRole.role_id == role_id)
            .all()
        ]
        query = query.filter(User.id.in_(user_ids)) if user_ids else query.filter(False)

    total = query.count()
    users = (
        query.order_by(User.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"items": user_reads(db, users), "total": total}


@router.post("", status_code=201)
def create_user(
    payload: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    if _find_user_by_name(db, payload.display_name) is not None:
        raise HTTPException(status_code=409, detail="用户名已存在")

    _require_roles(db, payload.role_ids)
    _validate_password_length(db, payload.password)
    user = User(
        display_name=payload.display_name.strip(),
        password_hash=hash_password(payload.password),
        is_active=payload.is_active,
    )
    db.add(user)
    db.flush()
    _replace_user_roles(db, user.id, payload.role_ids)
    record_operation_log(
        db,
        request,
        current_user,
        "user",
        "create",
        target_type="user",
        target_id=str(user.id),
        summary=f"创建用户 {user.display_name}",
        after_data=json.dumps(
            payload.model_dump(exclude={"password"}),
            ensure_ascii=False,
            default=str,
        ),
    )
    db.commit()
    return user_read(db, user)


@router.get("/{user_id}")
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
):
    return user_read(db, _require_user(db, user_id))


@router.patch("/{user_id}")
def update_user(
    user_id: int,
    payload: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    user = _require_user(db, user_id)
    before = json.dumps(user_read(db, user), ensure_ascii=False, default=str)

    if payload.display_name is not None:
        display_name = payload.display_name.strip()
        if not display_name:
            raise HTTPException(status_code=422, detail="用户名不能为空")
        existing = _find_user_by_name(db, display_name)
        if existing is not None and existing.id != user.id:
            raise HTTPException(status_code=409, detail="用户名已存在")
        user.display_name = display_name

    if payload.is_active is not None:
        if user.id == current_user.id and not payload.is_active:
            raise HTTPException(status_code=400, detail="不能禁用自己的账号")
        user.is_active = payload.is_active
        if not payload.is_active:
            revoke_all_sessions(db, user.id)

    if payload.role_ids is not None:
        _require_roles(db, payload.role_ids)
        _replace_user_roles(db, user.id, payload.role_ids)

    record_operation_log(
        db,
        request,
        current_user,
        "user",
        "update",
        target_type="user",
        target_id=str(user.id),
        summary=f"更新用户 {user.display_name}",
        before_data=before,
        after_data=json.dumps(user_read(db, user), ensure_ascii=False, default=str),
    )
    db.commit()
    return user_read(db, user)


@router.post("/{user_id}/reset-password")
def reset_password(
    user_id: int,
    payload: ResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    user = _require_user(db, user_id)
    _validate_password_length(db, payload.password)
    user.password_hash = hash_password(payload.password)
    revoke_all_sessions(db, user.id)
    record_operation_log(
        db,
        request,
        current_user,
        "user",
        "reset-password",
        target_type="user",
        target_id=str(user.id),
        summary=f"重置用户 {user.display_name} 密码",
    )
    db.commit()
    return {"status": "ok"}


@router.post("/{user_id}/force-logout")
def force_logout(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    user = _require_user(db, user_id)
    revoke_all_sessions(db, user.id)
    record_operation_log(
        db,
        request,
        current_user,
        "user",
        "force-logout",
        target_type="user",
        target_id=str(user.id),
        summary=f"强制下线用户 {user.display_name}",
    )
    db.commit()
    return {"status": "ok"}


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    user = _require_user(db, user_id)
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除当前登录账号")

    record_operation_log(
        db,
        request,
        current_user,
        "user",
        "delete",
        target_type="user",
        target_id=str(user.id),
        summary=f"删除用户 {user.display_name}",
    )
    db.delete(user)
    db.commit()
    return None
