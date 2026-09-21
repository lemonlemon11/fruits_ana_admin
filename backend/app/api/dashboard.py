"""管理端工作台统计接口。"""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import require_admin_user
from ..db import get_db
from ..models import (
    as_beijing_str,
    AdminLoginLog,
    AdminMenu,
    AdminOperationLog,
    AdminPermission,
    AdminRole,
    AdminUserRole,
    AiAnalysis,
    DataIssue,
    ImportBatch,
    SaleRecord,
    SettlementSummary,
    SourceFile,
    User,
    utc_now,
)
from ..schemas import DashboardStats


router = APIRouter(prefix="/api/admin/dashboard", tags=["admin-dashboard"])


@router.get("/stats", response_model=DashboardStats)
def stats(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
):
    now = utc_now()
    now_naive = now.replace(tzinfo=None)
    week_ago = now_naive - timedelta(days=6)

    user_total = db.query(User).count()
    user_active = db.query(User).filter(User.is_active.is_(True)).count()
    role_total = db.query(AdminRole).count()
    role_active = db.query(AdminRole).filter(AdminRole.is_active.is_(True)).count()
    permission_total = db.query(AdminPermission).count()
    permission_active = (
        db.query(AdminPermission)
        .filter(AdminPermission.is_active.is_(True))
        .count()
    )
    import_total = db.query(ImportBatch).count()
    issue_total = db.query(DataIssue).count()
    ai_cache_total = db.query(AiAnalysis).count()
    sale_record_total = db.query(SaleRecord).count()
    source_file_total = db.query(SourceFile).count()
    settlement_total = db.query(SettlementSummary).count()
    total_sales_amount = float(
        db.query(func.coalesce(func.sum(SaleRecord.amount), 0)).scalar() or 0
    )
    sale_date_range = (
        db.query(func.min(SaleRecord.sale_date), func.max(SaleRecord.sale_date))
        .one()
    )
    latest_import_at_value = db.query(func.max(ImportBatch.imported_at)).scalar()

    import_status_rows = (
        db.query(ImportBatch.status, func.count(ImportBatch.id))
        .group_by(ImportBatch.status)
        .all()
    )
    import_status = {row[0] or "unknown": row[1] for row in import_status_rows}

    issue_severity_rows = (
        db.query(DataIssue.severity, func.count(DataIssue.id))
        .group_by(DataIssue.severity)
        .all()
    )
    issue_severity = {row[0] or "unknown": row[1] for row in issue_severity_rows}

    grade_distribution_rows = (
        db.query(SaleRecord.grade, func.count(SaleRecord.id))
        .group_by(SaleRecord.grade)
        .order_by(SaleRecord.grade)
        .all()
    )
    grade_distribution = [
        {"name": row[0] or "未知", "value": row[1]}
        for row in grade_distribution_rows
    ]

    fruit_type_distribution_rows = (
        db.query(SaleRecord.fruit_type, func.count(SaleRecord.id))
        .group_by(SaleRecord.fruit_type)
        .order_by(func.count(SaleRecord.id).desc())
        .all()
    )
    fruit_type_distribution = [
        {"name": row[0] or "未知", "value": row[1]}
        for row in fruit_type_distribution_rows
    ]

    role_distribution_rows = (
        db.query(AdminRole.name, func.count(AdminUserRole.id))
        .join(AdminUserRole, AdminUserRole.role_id == AdminRole.id)
        .group_by(AdminRole.id, AdminRole.name)
        .order_by(func.count(AdminUserRole.id).desc())
        .all()
    )
    role_distribution = [
        {"name": row[0], "value": row[1]} for row in role_distribution_rows
    ]

    login_success_count = (
        db.query(AdminLoginLog)
        .filter(
            AdminLoginLog.success.is_(True),
            AdminLoginLog.created_at >= week_ago,
        )
        .count()
    )
    login_failed_count = (
        db.query(AdminLoginLog)
        .filter(
            AdminLoginLog.success.is_(False),
            AdminLoginLog.created_at >= week_ago,
        )
        .count()
    )

    login_trend_rows = (
        db.query(
            func.date(AdminLoginLog.created_at).label("day"),
            func.count(AdminLoginLog.id),
        )
        .filter(AdminLoginLog.created_at >= week_ago)
        .group_by(func.date(AdminLoginLog.created_at))
        .all()
    )
    login_by_day = {str(row[0]): row[1] for row in login_trend_rows}
    login_trend = []
    for offset in range(6, -1, -1):
        day = (now_naive.date() - timedelta(days=offset)).isoformat()
        login_trend.append({"date": day, "value": login_by_day.get(day, 0)})

    recent_logins = (
        db.query(AdminLoginLog)
        .order_by(AdminLoginLog.created_at.desc())
        .limit(6)
        .all()
    )
    recent_operations = (
        db.query(AdminOperationLog)
        .order_by(AdminOperationLog.created_at.desc())
        .limit(6)
        .all()
    )

    return {
        "user_total": user_total,
        "user_active": user_active,
        "user_disabled": user_total - user_active,
        "role_total": role_total,
        "role_active": role_active,
        "menu_total": db.query(AdminMenu).count(),
        "permission_total": permission_total,
        "permission_active": permission_active,
        "import_total": import_total,
        "issue_total": issue_total,
        "ai_cache_total": ai_cache_total,
        "login_total_7d": login_success_count,
        "login_failed_7d": login_failed_count,
        "import_status": import_status,
        "issue_severity": issue_severity,
        "login_trend_7d": login_trend,
        "role_distribution": role_distribution,
        "sale_record_total": sale_record_total,
        "source_file_total": source_file_total,
        "settlement_total": settlement_total,
        "total_sales_amount": total_sales_amount,
        "sales_date_start": (
            sale_date_range[0].isoformat() if sale_date_range[0] else None
        ),
        "sales_date_end": (
            sale_date_range[1].isoformat() if sale_date_range[1] else None
        ),
        "latest_import_at": (
            as_beijing_str(latest_import_at_value)
        ),
        "grade_distribution": grade_distribution,
        "fruit_type_distribution": fruit_type_distribution,
        "recent_logins": [
            {
                "id": item.id,
                "username": item.username,
                "success": item.success,
                "message": item.message,
                "ip": item.ip,
                "user_agent": item.user_agent,
                "created_at": as_beijing_str(item.created_at) or "",
            }
            for item in recent_logins
        ],
        "recent_operations": [
            {
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
                "created_at": as_beijing_str(item.created_at) or "",
            }
            for item in recent_operations
        ],
    }
