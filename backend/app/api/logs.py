"""管理端审计日志查询与导出接口。"""

from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..auth import require_admin_user
from ..db import get_db
from ..models import AdminLoginLog, AdminOperationLog, User, as_beijing_str


router = APIRouter(prefix="/api/admin/logs", tags=["admin-logs"])


def _login_log_dict(item: AdminLoginLog) -> dict:
    return {
        "id": item.id,
        "username": item.username,
        "success": item.success,
        "message": item.message,
        "ip": item.ip,
        "user_agent": item.user_agent,
        "created_at": as_beijing_str(item.created_at),
    }


def _operation_log_dict(item: AdminOperationLog) -> dict:
    return {
        "id": item.id,
        "username": item.username,
        "module": item.module,
        "action": item.action,
        "target_type": item.target_type,
        "target_id": item.target_id,
        "summary": item.summary,
        "status": item.status,
        "ip": item.ip,
        "user_agent": item.user_agent,
        "created_at": as_beijing_str(item.created_at),
    }


@router.get("/login")
def list_login_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    username: str | None = None,
    success: bool | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
):
    query = db.query(AdminLoginLog)
    if username:
        query = query.filter(AdminLoginLog.username.ilike(f"%{username}%"))
    if success is not None:
        query = query.filter(AdminLoginLog.success.is_(success))
    total = query.count()
    items = (
        query.order_by(AdminLoginLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"items": [_login_log_dict(item) for item in items], "total": total}


@router.get("/operations")
def list_operation_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    module: str | None = None,
    username: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
):
    query = db.query(AdminOperationLog)
    if module:
        query = query.filter(AdminOperationLog.module == module)
    if username:
        query = query.filter(AdminOperationLog.username.ilike(f"%{username}%"))
    total = query.count()
    items = (
        query.order_by(AdminOperationLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"items": [_operation_log_dict(item) for item in items], "total": total}


@router.get("/operations.csv")
def export_operation_logs(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
):
    items = db.query(AdminOperationLog).order_by(AdminOperationLog.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["id", "username", "module", "action", "target_type", "target_id", "summary", "status", "ip", "created_at"]
    )
    for item in items:
        writer.writerow(
            [
                item.id,
                item.username,
                item.module,
                item.action,
                item.target_type,
                item.target_id,
                item.summary,
                item.status,
                item.ip,
                as_beijing_str(item.created_at) or "",
            ]
        )
    payload = io.BytesIO(output.getvalue().encode("utf-8-sig"))
    return StreamingResponse(
        payload,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="admin-operations.csv"'},
    )


@router.get("/login.csv")
def export_login_logs(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
):
    items = db.query(AdminLoginLog).order_by(AdminLoginLog.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "username", "success", "message", "ip", "created_at"])
    for item in items:
        writer.writerow(
            [
                item.id,
                item.username,
                item.success,
                item.message,
                item.ip,
                as_beijing_str(item.created_at) or "",
            ]
        )
    payload = io.BytesIO(output.getvalue().encode("utf-8-sig"))
    return StreamingResponse(
        payload,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="admin-logins.csv"'},
    )
