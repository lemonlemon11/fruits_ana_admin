"""管理端角色管理接口。"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..auth import record_operation_log, require_permission
from ..db import get_db
from ..models import (
    AdminMenu,
    AdminPermission,
    AdminRole,
    AdminRoleMenu,
    AdminRolePermission,
    AdminUserRole,
    User,
)
from ..schemas import RoleCreate, RoleGrant, RoleListResponse, RoleUpdate
from ..serializers import role_read


router = APIRouter(prefix="/api/admin/roles", tags=["admin-roles"])


def _require_role(db: Session, role_id: int) -> AdminRole:
    role = db.get(AdminRole, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="角色不存在")
    return role


@router.get("", response_model=RoleListResponse)
def list_roles(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("admin:role:view")),
):
    roles = db.query(AdminRole).order_by(AdminRole.id).all()
    return {"items": [role_read(db, role) for role in roles], "total": len(roles)}


@router.post("", status_code=201)
def create_role(
    payload: RoleCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("admin:role:create")),
):
    exists = db.query(AdminRole).filter(AdminRole.code == payload.code).first()
    if exists is not None:
        raise HTTPException(status_code=409, detail="角色编码已存在")

    role = AdminRole(
        code=payload.code,
        name=payload.name,
        description=payload.description,
        is_active=payload.is_active,
    )
    db.add(role)
    db.flush()
    record_operation_log(
        db,
        request,
        current_user,
        "role",
        "create",
        target_type="role",
        target_id=str(role.id),
        summary=f"创建角色 {role.name}",
        after_data=json.dumps(payload.model_dump(), ensure_ascii=False),
    )
    db.commit()
    return role_read(db, role)


@router.get("/{role_id}")
def get_role(
    role_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("admin:role:view")),
):
    return role_read(db, _require_role(db, role_id))


@router.patch("/{role_id}")
def update_role(
    role_id: int,
    payload: RoleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("admin:role:update")),
):
    role = _require_role(db, role_id)
    before = json.dumps(role_read(db, role), ensure_ascii=False, default=str)
    if payload.name is not None:
        role.name = payload.name
    if payload.description is not None:
        role.description = payload.description
    if payload.is_active is not None:
        if role.code in {"super_admin", "fruit_admin"} and not payload.is_active:
            raise HTTPException(status_code=400, detail="不能停用系统管理员角色")
        role.is_active = payload.is_active
    record_operation_log(
        db,
        request,
        current_user,
        "role",
        "update",
        target_type="role",
        target_id=str(role.id),
        summary=f"更新角色 {role.name}",
        before_data=before,
        after_data=json.dumps(role_read(db, role), ensure_ascii=False, default=str),
    )
    db.commit()
    return role_read(db, role)


@router.put("/{role_id}/grant")
def grant_role(
    role_id: int,
    payload: RoleGrant,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("admin:role:grant")),
):
    role = _require_role(db, role_id)
    if role.code in {"super_admin", "fruit_admin"}:
        raise HTTPException(status_code=400, detail="系统管理员角色始终拥有全部权限，无需调整")

    menus = db.query(AdminMenu).filter(AdminMenu.id.in_(payload.menu_ids)).all()
    permissions = (
        db.query(AdminPermission)
        .filter(AdminPermission.id.in_(payload.permission_ids))
        .all()
    )
    if len(menus) != len(set(payload.menu_ids)) or len(permissions) != len(
        set(payload.permission_ids)
    ):
        raise HTTPException(status_code=422, detail="存在无效菜单或权限")

    db.query(AdminRoleMenu).filter(AdminRoleMenu.role_id == role.id).delete()
    db.query(AdminRolePermission).filter(
        AdminRolePermission.role_id == role.id
    ).delete()
    for menu_id in payload.menu_ids:
        db.add(AdminRoleMenu(role_id=role.id, menu_id=menu_id))
    for permission_id in payload.permission_ids:
        db.add(AdminRolePermission(role_id=role.id, permission_id=permission_id))

    record_operation_log(
        db,
        request,
        current_user,
        "role",
        "grant",
        target_type="role",
        target_id=str(role.id),
        summary=f"调整角色 {role.name} 权限",
        after_data=json.dumps(payload.model_dump(), ensure_ascii=False),
    )
    db.commit()
    return role_read(db, role)


@router.delete("/{role_id}", status_code=204)
def delete_role(
    role_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("admin:role:delete")),
):
    role = _require_role(db, role_id)
    if role.is_system or role.code in {"super_admin", "fruit_admin"}:
        raise HTTPException(status_code=400, detail="系统预置角色不能删除")
    user_count = db.query(AdminUserRole).filter(AdminUserRole.role_id == role.id).count()
    if user_count:
        raise HTTPException(status_code=400, detail="角色仍被用户使用，不能删除")

    record_operation_log(
        db,
        request,
        current_user,
        "role",
        "delete",
        target_type="role",
        target_id=str(role.id),
        summary=f"删除角色 {role.name}",
    )
    db.delete(role)
    db.commit()
    return None
