"""管理端 API 请求与响应模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=128)
    remember_me: bool = False


class RoleBrief(BaseModel):
    id: int
    code: str
    name: str


class PermissionBrief(BaseModel):
    id: int
    code: str
    name: str


class MenuBrief(BaseModel):
    id: int
    parent_id: int | None
    name: str
    menu_type: str
    route_path: str | None
    component: str | None
    icon: str | None
    permission_code: str | None
    sort_order: int
    is_active: bool
    children: list["MenuBrief"] = []


class AuthUser(BaseModel):
    id: int
    display_name: str
    is_active: bool
    roles: list[RoleBrief] = []
    permissions: list[str] = []
    menus: list[MenuBrief] = []


class AuthResponse(BaseModel):
    user: AuthUser


class UserCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=8, max_length=128)
    role_ids: list[int] = []
    is_active: bool = True


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    is_active: bool | None = None
    role_ids: list[int] | None = None


class ResetPasswordRequest(BaseModel):
    password: str = Field(min_length=8, max_length=128)


class UserRead(BaseModel):
    id: int
    display_name: str
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None
    roles: list[RoleBrief] = []


class UserListResponse(BaseModel):
    items: list[UserRead]
    total: int


class RoleCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=1, max_length=80)
    description: str | None = None
    is_active: bool = True


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = None
    is_active: bool | None = None


class RoleGrant(BaseModel):
    menu_ids: list[int] = []
    permission_ids: list[int] = []


class RoleRead(BaseModel):
    id: int
    code: str
    name: str
    description: str | None
    is_system: bool
    is_active: bool
    user_count: int = 0
    menu_ids: list[int] = []
    permission_ids: list[int] = []


class RoleListResponse(BaseModel):
    items: list[RoleRead]
    total: int


class MenuCreate(BaseModel):
    parent_id: int | None = None
    name: str = Field(min_length=1, max_length=80)
    menu_type: str = Field(default="menu", pattern=r"^(directory|menu|button)$")
    route_path: str | None = None
    component: str | None = None
    icon: str | None = None
    permission_code: str | None = None
    sort_order: int = 0
    is_active: bool = True


class MenuUpdate(BaseModel):
    parent_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=80)
    menu_type: str | None = Field(default=None, pattern=r"^(directory|menu|button)$")
    route_path: str | None = None
    component: str | None = None
    icon: str | None = None
    permission_code: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class MenuRead(MenuCreate, ORMModel):
    id: int
    children: list["MenuRead"] = []


class PermissionCreate(BaseModel):
    code: str = Field(min_length=3, max_length=80, pattern=r"^[a-z][a-z0-9:_-]*$")
    name: str = Field(min_length=1, max_length=80)
    module: str = Field(default="admin", min_length=1, max_length=64)
    permission_type: str = Field(default="action", pattern=r"^(menu|action|api|data)$")
    description: str | None = None
    is_active: bool = True


class PermissionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    module: str | None = Field(default=None, min_length=1, max_length=64)
    permission_type: str | None = Field(
        default=None, pattern=r"^(menu|action|api|data)$"
    )
    description: str | None = None
    is_active: bool | None = None


class PermissionRead(PermissionCreate, ORMModel):
    id: int


class PermissionListResponse(BaseModel):
    items: list[PermissionRead]
    total: int


class NotificationCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=1)
    notification_type: str = Field(
        default="announcement", pattern=r"^(announcement|task|system)$"
    )
    priority: str = Field(default="normal", pattern=r"^(normal|important|urgent)$")
    target_type: str = Field(default="all", pattern=r"^(all|role|user)$")
    target_role_ids: list[int] = []
    target_user_ids: list[int] = []
    is_published: bool = False
    publish_at: datetime | None = None
    expire_at: datetime | None = None


class NotificationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    content: str | None = Field(default=None, min_length=1)
    notification_type: str | None = Field(
        default=None, pattern=r"^(announcement|task|system)$"
    )
    priority: str | None = Field(default=None, pattern=r"^(normal|important|urgent)$")
    target_type: str | None = Field(default=None, pattern=r"^(all|role|user)$")
    target_role_ids: list[int] | None = None
    target_user_ids: list[int] | None = None
    is_published: bool | None = None
    publish_at: datetime | None = None
    expire_at: datetime | None = None


class NotificationRead(BaseModel):
    id: int
    title: str
    content: str
    notification_type: str
    priority: str
    target_type: str
    target_role_ids: list[int]
    target_user_ids: list[int]
    is_published: bool
    publish_at: datetime | None
    expire_at: datetime | None
    created_by: int | None
    created_at: datetime
    updated_at: datetime
    recipient_total: int
    read_count: int
    unread_count: int


class NotificationRecipientRead(BaseModel):
    user_id: int
    display_name: str
    is_read: bool
    read_at: datetime | None


class NotificationDetail(NotificationRead):
    recipients: list[NotificationRecipientRead] = []


class NotificationListResponse(BaseModel):
    items: list[NotificationRead]
    total: int


class SettingRead(BaseModel):
    key: str
    value: str | None
    description: str | None


class SettingUpdate(BaseModel):
    value: str | None = None
    description: str | None = None


class LoginLogRead(BaseModel):
    id: int
    username: str | None
    success: bool
    message: str | None
    ip: str | None
    user_agent: str | None
    created_at: datetime


class OperationLogRead(BaseModel):
    id: int
    username: str | None
    module: str
    action: str
    target_type: str | None
    target_id: str | None
    summary: str | None
    status: str
    ip: str | None
    user_agent: str | None
    created_at: datetime


class LogListResponse(BaseModel):
    items: list[Any]
    total: int


class DashboardTrendPoint(BaseModel):
    date: str
    value: int


class DashboardDistributionItem(BaseModel):
    name: str
    value: int


class DashboardStats(BaseModel):
    user_total: int
    user_active: int
    user_disabled: int
    role_total: int
    role_active: int
    menu_total: int
    permission_total: int
    permission_active: int
    import_total: int
    issue_total: int
    ai_cache_total: int
    login_total_7d: int
    login_failed_7d: int
    import_status: dict[str, int]
    issue_severity: dict[str, int]
    login_trend_7d: list[DashboardTrendPoint]
    role_distribution: list[DashboardDistributionItem]
    recent_logins: list[LoginLogRead]
    recent_operations: list[OperationLogRead]
    sale_record_total: int
    source_file_total: int
    settlement_total: int
    total_sales_amount: float
    sales_date_start: str | None
    sales_date_end: str | None
    latest_import_at: str | None
    grade_distribution: list[DashboardDistributionItem]
    fruit_type_distribution: list[DashboardDistributionItem]
