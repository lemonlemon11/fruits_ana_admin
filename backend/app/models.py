"""管理端持久化模型。

业务表只做只读映射，管理端新增表使用 `admin_` 前缀，避免与 `fruits_ana`
现有业务模型冲突。
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import DATETIME as MySQLDateTime
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def utc_now() -> datetime:
    """返回带时区的当前 UTC 时间。"""

    return datetime.now(timezone.utc)


PRECISE_DATETIME = DateTime(timezone=True).with_variant(
    MySQLDateTime(fsp=6),
    "mysql",
)


class User(Base):
    """只读映射现有 `fruits_ana` 用户表。"""

    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        PRECISE_DATETIME, default=utc_now, nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        PRECISE_DATETIME, nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class UserSession(Base):
    """只读映射现有服务端会话表。"""

    __tablename__ = "user_session"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        PRECISE_DATETIME, default=utc_now, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(PRECISE_DATETIME, nullable=False)


class ImportBatch(Base):
    """只读映射现有导入批次表。"""

    __tablename__ = "import_batch"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    merchant_no: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    merchant_no_normalized: Mapped[str | None] = mapped_column(String(128), nullable=True)
    order_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
    order_no_normalized: Mapped[str | None] = mapped_column(String(128), nullable=True)
    container_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
    vehicle_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
    imported_at: Mapped[datetime] = mapped_column(
        PRECISE_DATETIME, default=utc_now, nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    success_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    warning_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)


class SourceFile(Base):
    """只读映射现有原始文件表。"""

    __tablename__ = "source_file"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    import_batch_id: Mapped[int] = mapped_column(
        ForeignKey("import_batch.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    storage_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    stored_at: Mapped[datetime] = mapped_column(
        PRECISE_DATETIME, default=utc_now, nullable=False
    )


class SaleRecord(Base):
    """只读映射现有销售事实表。"""

    __tablename__ = "sale_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    import_batch_id: Mapped[int | None] = mapped_column(
        ForeignKey("import_batch.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_file.id", ondelete="SET NULL"), nullable=True, index=True
    )
    sale_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    fruit_type: Mapped[str] = mapped_column(String(64), default="榴莲", nullable=False)
    grade_raw: Mapped[str | None] = mapped_column(String(64), nullable=True)
    grade: Mapped[str] = mapped_column(String(1), nullable=False)
    spec_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    sales_region: Mapped[str | None] = mapped_column(String(128), nullable=True)


class SettlementSummary(Base):
    """只读映射现有结算摘要表。"""

    __tablename__ = "settlement_summary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    import_batch_id: Mapped[int] = mapped_column(
        ForeignKey("import_batch.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sales_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    after_sale_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 4), nullable=True
    )
    goods_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    fee_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    fee_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    customs_tax: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    payable_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)


class DataIssue(Base):
    """只读映射现有数据问题表。"""

    __tablename__ = "data_issue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    import_batch_id: Mapped[int] = mapped_column(
        ForeignKey("import_batch.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_file.id", ondelete="SET NULL"), nullable=True
    )
    sale_record_id: Mapped[int | None] = mapped_column(
        ForeignKey("sale_record.id", ondelete="SET NULL"), nullable=True
    )
    row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    issue_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default="warning", nullable=False)
    field_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    raw_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        PRECISE_DATETIME, default=utc_now, nullable=False
    )


class AiAnalysis(Base):
    """只读映射现有 AI 分析缓存表。"""

    __tablename__ = "ai_analysis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cache_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    feature: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        PRECISE_DATETIME, default=utc_now, nullable=False
    )


class AdminRole(Base):
    """管理员角色。"""

    __tablename__ = "admin_role"
    __table_args__ = (
        Index("ux_admin_role_code", "code", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        PRECISE_DATETIME, default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        PRECISE_DATETIME, default=utc_now, onupdate=utc_now, nullable=False
    )


class AdminPermission(Base):
    """权限点。"""

    __tablename__ = "admin_permission"
    __table_args__ = (
        Index("ux_admin_permission_code", "code", unique=True),
        Index("ix_admin_permission_module", "module"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    module: Mapped[str] = mapped_column(String(64), default="admin", nullable=False)
    permission_type: Mapped[str] = mapped_column(
        String(16), default="action", nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        PRECISE_DATETIME, default=utc_now, nullable=False
    )


class AdminMenu(Base):
    """管理端菜单与按钮树。"""

    __tablename__ = "admin_menu"
    __table_args__ = (
        Index("ix_admin_menu_parent_id", "parent_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("admin_menu.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    menu_type: Mapped[str] = mapped_column(String(16), default="menu", nullable=False)
    route_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    component: Mapped[str | None] = mapped_column(String(255), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(64), nullable=True)
    permission_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        PRECISE_DATETIME, default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        PRECISE_DATETIME, default=utc_now, onupdate=utc_now, nullable=False
    )


class AdminAccess(Base):
    """管理端控制台访问授权。

    与业务 RBAC 分离：业务角色/菜单/权限用于 `fruits_ana` 用户系统，
    此表只决定哪些账号能登录当前管理端控制台。
    """

    __tablename__ = "admin_access"
    __table_args__ = (
        Index("ux_admin_access_user_id", "user_id", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_super_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        PRECISE_DATETIME, default=utc_now, nullable=False
    )


class AdminUserRole(Base):
    """用户与角色关系。"""

    __tablename__ = "admin_user_role"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="ux_admin_user_role"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_id: Mapped[int] = mapped_column(
        ForeignKey("admin_role.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        PRECISE_DATETIME, default=utc_now, nullable=False
    )


class AdminRoleMenu(Base):
    """角色与菜单关系。"""

    __tablename__ = "admin_role_menu"
    __table_args__ = (
        UniqueConstraint("role_id", "menu_id", name="ux_admin_role_menu"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_id: Mapped[int] = mapped_column(
        ForeignKey("admin_role.id", ondelete="CASCADE"), nullable=False, index=True
    )
    menu_id: Mapped[int] = mapped_column(
        ForeignKey("admin_menu.id", ondelete="CASCADE"), nullable=False, index=True
    )


class AdminRolePermission(Base):
    """角色与权限点关系。"""

    __tablename__ = "admin_role_permission"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="ux_admin_role_permission"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_id: Mapped[int] = mapped_column(
        ForeignKey("admin_role.id", ondelete="CASCADE"), nullable=False, index=True
    )
    permission_id: Mapped[int] = mapped_column(
        ForeignKey("admin_permission.id", ondelete="CASCADE"), nullable=False, index=True
    )


class AdminOperationLog(Base):
    """管理端操作审计日志。"""

    __tablename__ = "admin_operation_log"
    __table_args__ = (
        Index("ix_admin_operation_log_created_at", "created_at"),
        Index("ix_admin_operation_log_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    username: Mapped[str | None] = mapped_column(String(80), nullable=True)
    module: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    before_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    after_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="success", nullable=False)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        PRECISE_DATETIME, default=utc_now, nullable=False
    )


class AdminLoginLog(Base):
    """管理端登录审计日志。"""

    __tablename__ = "admin_login_log"
    __table_args__ = (
        Index("ix_admin_login_log_created_at", "created_at"),
        Index("ix_admin_login_log_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    username: Mapped[str | None] = mapped_column(String(80), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        PRECISE_DATETIME, default=utc_now, nullable=False
    )


class AdminSetting(Base):
    """管理端系统配置。"""

    __tablename__ = "admin_setting"
    __table_args__ = (
        Index("ux_admin_setting_key", "key", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(80), nullable=False)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        PRECISE_DATETIME, default=utc_now, onupdate=utc_now, nullable=False
    )


class AdminNotification(Base):
    """管理端下发的站内通知。"""

    __tablename__ = "admin_notification"
    __table_args__ = (
        Index("ix_admin_notification_created_at", "created_at"),
        Index("ix_admin_notification_publish_at", "publish_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[str] = mapped_column(
        String(32), default="announcement", nullable=False
    )
    priority: Mapped[str] = mapped_column(
        String(16), default="normal", nullable=False
    )
    target_type: Mapped[str] = mapped_column(
        String(16), default="all", nullable=False
    )
    target_role_ids: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_user_ids: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    publish_at: Mapped[datetime | None] = mapped_column(PRECISE_DATETIME, nullable=True)
    expire_at: Mapped[datetime | None] = mapped_column(PRECISE_DATETIME, nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        PRECISE_DATETIME, default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        PRECISE_DATETIME, default=utc_now, onupdate=utc_now, nullable=False
    )


class AdminNotificationRecipient(Base):
    """通知收件人与阅读状态。"""

    __tablename__ = "admin_notification_recipient"
    __table_args__ = (
        Index(
            "ux_admin_notification_recipient",
            "notification_id",
            "user_id",
            unique=True,
        ),
        Index("ix_admin_notification_recipient_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    notification_id: Mapped[int] = mapped_column(
        ForeignKey("admin_notification.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(PRECISE_DATETIME, nullable=True)
    last_reminded_at: Mapped[datetime | None] = mapped_column(
        PRECISE_DATETIME, nullable=True
    )
    remind_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        PRECISE_DATETIME, default=utc_now, nullable=False
    )


__all__ = [
    "AdminAccess",
    "AdminLoginLog",
    "AdminMenu",
    "AdminNotification",
    "AdminNotificationRecipient",
    "AdminOperationLog",
    "AdminPermission",
    "AdminRole",
    "AdminRoleMenu",
    "AdminRolePermission",
    "AdminSetting",
    "AdminUserRole",
    "AiAnalysis",
    "DataIssue",
    "ImportBatch",
    "SaleRecord",
    "SettlementSummary",
    "SourceFile",
    "User",
    "UserSession",
]
