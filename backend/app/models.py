"""管理端持久化模型。

业务表只做只读映射，管理端新增表使用 `admin_` 前缀，避免与 `fruits_ana`
现有业务模型冲突。
"""

from __future__ import annotations

from datetime import date, datetime, timezone
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
    text,
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
    # server_default 与迁移脚本 add_entry_schema.py 的 `DEFAULT 'import'` 对齐，
    # 避免 create_all 与迁移脚本两条建表路径产出不同 DDL。
    source_type: Mapped[str] = mapped_column(
        String(16), default="import", server_default=text("'import'"), nullable=False
    )
    market: Mapped[str | None] = mapped_column(String(128), nullable=True)
    arrival_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    arrival_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
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
    # 业务端 `grade` 由枚举映射为 varchar(5)（含 OTHER），此处保持同长度避免 schema 漂移。
    grade: Mapped[str] = mapped_column(String(5), nullable=False)
    spec_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    piece_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    spec_kg: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
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


class EntryFieldOption(Base):
    """录单字段字典，与 fruits_ana 共享；管理端负责维护。"""

    __tablename__ = "entry_field_option"
    __table_args__ = (
        Index("ux_entry_field_option", "field_key", "value", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    field_key: Mapped[str] = mapped_column(String(32), nullable=False)
    value: Mapped[str] = mapped_column(String(64), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        PRECISE_DATETIME, default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        PRECISE_DATETIME, default=utc_now, onupdate=utc_now, nullable=False
    )


class FieldConversionRule(Base):
    """通用字段转换规则，管理端维护，业务端读取后只影响统计，不改变录入展示。"""

    __tablename__ = "admin_field_conversion_rule"
    __table_args__ = (
        Index("ux_admin_field_conversion_rule", "field_key", "source_value", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    field_key: Mapped[str] = mapped_column(String(32), nullable=False)
    source_value: Mapped[str] = mapped_column(String(64), nullable=False)
    target_value: Mapped[str] = mapped_column(String(64), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        PRECISE_DATETIME, default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        PRECISE_DATETIME, default=utc_now, onupdate=utc_now, nullable=False
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
    "EntryFieldOption",
    "FieldConversionRule",
    "ImportBatch",
    "SaleRecord",
    "SettlementSummary",
    "SourceFile",
    "User",
    "UserSession",
]


# 数据库列注释：统一给所有已注册模型补 MySQL `COMMENT`。
# 放在模型定义之后、应用启动前的 `Base.metadata.create_all` 之前生效。
FIELD_COMMENTS: dict[str, str] = {
    "id": "主键",
    "action": "操作类型",
    "after_data": "变更后数据",
    "after_sale_amount": "售后金额",
    "amount": "金额",
    "arrival_date": "到达日期",
    "arrival_quantity": "到货数量",
    "before_data": "变更前数据",
    "brand": "品牌",
    "cache_key": "缓存键",
    "change_type": "变更类型",
    "changed_at": "修改时间",
    "changed_by": "修改人",
    "code": "编码",
    "component": "前端组件",
    "computed_quantity": "计算数量",
    "computed_sales_amount": "计算销售额",
    "confidence": "置信度",
    "confirmed_at": "确认时间",
    "confirmed_by": "确认人",
    "confirmed_count": "已确认数量",
    "container_no": "柜号",
    "content": "内容",
    "created_at": "创建时间",
    "created_by": "创建人",
    "customs_tax": "清关税费",
    "description": "描述",
    "display_name": "显示名称（登录用户名）",
    "draft_count": "草稿数",
    "error_summary": "错误摘要",
    "expire_at": "过期时间",
    "expires_at": "过期时间",
    "failure_count": "失败数",
    "feature": "功能标识",
    "fee_amount": "费用金额",
    "fee_detail": "费用明细",
    "fee_kind": "费用类型",
    "field_key": "字段标识",
    "field_name": "字段名",
    "file_after_sale_amount": "文件售后金额",
    "file_count": "文件数",
    "file_customs_tax": "文件清关税费",
    "file_fee_amount": "文件费用金额",
    "file_fee_detail": "文件费用明细",
    "file_goods_amount": "文件货款金额",
    "file_hash": "文件哈希",
    "file_name": "文件名",
    "file_payable_amount": "文件应付金额",
    "file_sales_amount": "文件销售额",
    "file_sales_quantity": "文件销售数量",
    "fruit_type": "水果类型",
    "goods_amount": "货款金额",
    "grade": "等级",
    "grade_raw": "原始等级",
    "icon": "图标",
    "import_batch_id": "导入批次ID",
    "import_draft_id": "导入草稿ID",
    "import_job_id": "导入任务ID",
    "imported_at": "导入时间",
    "ip": "IP地址",
    "is_active": "是否启用",
    "is_custom": "是否自定义",
    "is_published": "是否发布",
    "is_read": "是否已读",
    "is_super_admin": "是否超级管理员",
    "is_system": "是否系统内置",
    "issue_count": "问题数量",
    "issue_type": "问题类型",
    "item_type": "项目类型",
    "key": "配置键",
    "last_login_at": "最后登录时间",
    "last_reminded_at": "最近提醒时间",
    "manual_edit_count": "人工修改数",
    "market": "市场",
    "menu_id": "菜单ID",
    "menu_type": "菜单类型",
    "merchant_no": "商号",
    "merchant_no_normalized": "规范化商号",
    "message": "消息",
    "model": "模型",
    "module": "模块",
    "name": "名称",
    "needs_review": "是否需要复核",
    "new_value": "新值",
    "notification_id": "通知ID",
    "notification_type": "通知类型",
    "old_value": "旧值",
    "order_no": "单号",
    "order_no_normalized": "规范化单号",
    "origin": "来源",
    "original_payload": "原始载荷",
    "parent_id": "父级ID",
    "parse_confidence": "解析置信度",
    "parse_mode": "解析方式",
    "parse_model": "解析模型",
    "parse_profile": "解析配置",
    "password_hash": "密码哈希",
    "payable_amount": "应付金额",
    "payload": "载荷",
    "permission_code": "权限编码",
    "permission_id": "权限ID",
    "permission_type": "权限类型",
    "piece_count": "件数",
    "piece_count_max": "件数上限",
    "piece_count_min": "件数下限",
    "priority": "优先级",
    "publish_at": "发布时间",
    "quantity": "数量",
    "raw_row_text": "原始行文本",
    "raw_value": "原始值",
    "read_at": "阅读时间",
    "reason": "原因",
    "reconcile_detail": "对账明细",
    "reconcile_status": "对账状态",
    "remark": "备注",
    "remind_count": "提醒次数",
    "resolved": "是否已解决",
    "resolved_at": "解决时间",
    "resolved_by": "解决人",
    "review_note": "复核备注",
    "role_id": "角色ID",
    "route_path": "路由路径",
    "row_count": "行数",
    "row_number": "行号",
    "sale_date": "销售日期",
    "sale_record_id": "销售记录ID",
    "sales_amount": "销售额",
    "sales_quantity": "销售数量",
    "sales_region": "销售区域",
    "section": "区块",
    "severity": "严重程度",
    "sheet_name": "工作表名",
    "sort_order": "排序",
    "source_file_id": "源文件ID",
    "source_row": "源行号",
    "source_type": "来源类型",
    "source_value": "源值",
    "spec_kg": "规格重量",
    "spec_kg_max": "规格重量上限",
    "spec_kg_min": "规格重量下限",
    "spec_raw": "原始规格",
    "status": "状态",
    "storage_path": "存储路径",
    "stored_at": "存储时间",
    "success": "是否成功",
    "success_count": "成功数",
    "suffix": "后缀",
    "summary": "摘要",
    "target_id": "目标ID",
    "target_role_ids": "目标角色ID列表",
    "target_type": "目标类型",
    "target_user_ids": "目标用户ID列表",
    "target_value": "目标值",
    "title": "标题",
    "token": "令牌",
    "token_hash": "令牌哈希",
    "unit_price": "单价",
    "updated_at": "更新时间",
    "updated_by": "更新人",
    "user_agent": "用户代理",
    "user_id": "用户ID",
    "username": "用户名",
    "value": "值",
    "vehicle_no": "转运车号",
    "version": "版本",
    "warning_count": "警告数",
}


for _table in Base.metadata.tables.values():
    for _column in _table.columns:
        _comment = FIELD_COMMENTS.get(_column.name)
        if _comment:
            _column.comment = _comment
