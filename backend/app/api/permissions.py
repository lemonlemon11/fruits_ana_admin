"""管理端权限点管理接口。"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from ..auth import record_operation_log, require_permission
from ..db import get_db
from ..models import AdminPermission, AdminRolePermission, User
from ..schemas import PermissionCreate, PermissionListResponse, PermissionUpdate
from ..serializers import permission_read


router = APIRouter(prefix="/api/admin/permissions", tags=["admin-permissions"])


def _require_permission(db: Session, permission_id: int) -> AdminPermission:
    item = db.get(AdminPermission, permission_id)
    if item is None:
        raise HTTPException(status_code=404, detail="权限点不存在")
    return item


@router.get("", response_model=PermissionListResponse)
def list_permissions(
    keyword: str | None = None,
    module: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("admin:permission:view")),
):
    query = db.query(AdminPermission)
    if keyword:
        query = query.filter(
            (AdminPermission.code.ilike(f"%{keyword}%"))
            | (AdminPermission.name.ilike(f"%{keyword}%"))
        )
    if module:
        query = query.filter(AdminPermission.module == module)
    items = query.order_by(AdminPermission.module, AdminPermission.id).all()
    return {"items": [permission_read(item) for item in items], "total": len(items)}


@router.post("", status_code=201)
def create_permission(
    payload: PermissionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("admin:permission:create")),
):
    exists = db.query(AdminPermission).filter(AdminPermission.code == payload.code).first()
    if exists is not None:
        raise HTTPException(status_code=409, detail="权限编码已存在")

    item = AdminPermission(**payload.model_dump())
    db.add(item)
    db.flush()
    record_operation_log(
        db,
        request,
        current_user,
        "permission",
        "create",
        target_type="permission",
        target_id=str(item.id),
        summary=f"创建权限点 {item.name}",
        after_data=json.dumps(payload.model_dump(), ensure_ascii=False),
    )
    db.commit()
    return permission_read(item)


@router.patch("/{permission_id}")
def update_permission(
    permission_id: int,
    payload: PermissionUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("admin:permission:update")),
):
    item = _require_permission(db, permission_id)
    before = json.dumps(permission_read(item), ensure_ascii=False, default=str)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    record_operation_log(
        db,
        request,
        current_user,
        "permission",
        "update",
        target_type="permission",
        target_id=str(item.id),
        summary=f"更新权限点 {item.name}",
        before_data=before,
        after_data=json.dumps(permission_read(item), ensure_ascii=False, default=str),
    )
    db.commit()
    return permission_read(item)


@router.delete("/{permission_id}", status_code=204)
def delete_permission(
    permission_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("admin:permission:delete")),
):
    item = _require_permission(db, permission_id)
    references = (
        db.query(AdminRolePermission)
        .filter(AdminRolePermission.permission_id == permission_id)
        .count()
    )
    if references:
        raise HTTPException(status_code=400, detail="权限点已被角色引用，不能删除")

    record_operation_log(
        db,
        request,
        current_user,
        "permission",
        "delete",
        target_type="permission",
        target_id=str(item.id),
        summary=f"删除权限点 {item.name}",
    )
    db.delete(item)
    db.commit()
    return None
