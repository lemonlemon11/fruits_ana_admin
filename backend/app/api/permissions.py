"""用户端业务权限点只读目录，供角色授权页选择。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..auth import require_admin_user
from ..db import get_db
from ..models import AdminPermission, User
from ..schemas import PermissionListResponse
from ..serializers import permission_read


router = APIRouter(prefix="/api/admin/permissions", tags=["admin-permissions"])


@router.get("", response_model=PermissionListResponse)
def list_business_permissions(
    keyword: str | None = None,
    module: str | None = None,
    scope: str | None = Query(default=None, pattern=r"^(all|business)$"),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
):
    """只返回用户端业务权限点，管理端不再维护控制台权限点。"""

    query = db.query(AdminPermission).filter(AdminPermission.module != "admin")
    if keyword:
        query = query.filter(
            (AdminPermission.code.ilike(f"%{keyword}%"))
            | (AdminPermission.name.ilike(f"%{keyword}%"))
        )
    if module:
        query = query.filter(AdminPermission.module == module)
    items = query.order_by(AdminPermission.module, AdminPermission.id).all()
    return {"items": [permission_read(item) for item in items], "total": len(items)}
