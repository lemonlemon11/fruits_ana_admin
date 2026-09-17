export type RoleBrief = {
  id: number
  code: string
  name: string
}

export type MenuNode = {
  id: number
  parent_id: number | null
  name: string
  menu_type: 'directory' | 'menu' | 'button'
  route_path: string | null
  component: string | null
  icon: string | null
  permission_code: string | null
  sort_order: number
  is_active: boolean
  children: MenuNode[]
}

export type AuthUser = {
  id: number
  display_name: string
  is_active: boolean
  roles: RoleBrief[]
  permissions: string[]
  menus: MenuNode[]
}

export type UserItem = {
  id: number
  display_name: string
  is_active: boolean
  created_at: string
  last_login_at: string | null
  roles: RoleBrief[]
}

export type RoleItem = {
  id: number
  code: string
  name: string
  description: string | null
  is_system: boolean
  is_active: boolean
  user_count: number
  menu_ids: number[]
  permission_ids: number[]
}

export type PermissionItem = {
  id: number
  code: string
  name: string
  module: string
  permission_type: 'menu' | 'action' | 'api' | 'data'
  description: string | null
  is_active: boolean
}

export type NotificationItem = {
  id: number
  title: string
  content: string
  notification_type: 'announcement' | 'task' | 'system'
  priority: 'normal' | 'important' | 'urgent'
  target_type: 'all' | 'role' | 'user'
  target_role_ids: number[]
  target_user_ids: number[]
  is_published: boolean
  publish_at: string | null
  expire_at: string | null
  created_by: number | null
  created_at: string
  updated_at: string
  recipient_total: number
  read_count: number
  unread_count: number
}

export type MenuItem = {
  id: number
  parent_id: number | null
  name: string
  menu_type: 'directory' | 'menu' | 'button'
  route_path: string | null
  component: string | null
  icon: string | null
  permission_code: string | null
  sort_order: number
  is_active: boolean
  children: MenuNode[]
}

export type ListResponse<T> = {
  items: T[]
  total: number
}

export type DashboardStats = {
  user_total: number
  user_active: number
  user_disabled: number
  role_total: number
  role_active: number
  menu_total: number
  permission_total: number
  permission_active: number
  import_total: number
  issue_total: number
  ai_cache_total: number
  login_total_7d: number
  login_failed_7d: number
  import_status: Record<string, number>
  issue_severity: Record<string, number>
  login_trend_7d: Array<{ date: string; value: number }>
  role_distribution: Array<{ name: string; value: number }>
  recent_logins: LoginLogItem[]
  recent_operations: OperationLogItem[]
  sale_record_total: number
  source_file_total: number
  settlement_total: number
  total_sales_amount: number
  sales_date_start: string | null
  sales_date_end: string | null
  latest_import_at: string | null
  grade_distribution: Array<{ name: string; value: number }>
  fruit_type_distribution: Array<{ name: string; value: number }>
}

export type ImportBatchItem = {
  id: number
  file_name: string | null
  merchant_no: string
  merchant_no_normalized: string | null
  order_no: string | null
  order_no_normalized: string | null
  container_no: string | null
  vehicle_no: string | null
  imported_at: string | null
  status: string
  success_count: number
  warning_count: number
  failure_count: number
  error_summary: string | null
}

export type DataIssueItem = {
  id: number
  import_batch_id: number
  row_number: number | null
  issue_type: string
  severity: string
  field_name: string | null
  message: string
  raw_value: string | null
  created_at: string | null
}

export type AiCacheItem = {
  id: number
  cache_key: string
  feature: string
  model: string
  content: string
  created_at: string | null
}

export type LoginLogItem = {
  id: number
  username: string | null
  success: boolean
  message: string | null
  ip: string | null
  user_agent: string | null
  created_at: string
}

export type OperationLogItem = {
  id: number
  username: string | null
  module: string
  action: string
  target_type: string | null
  target_id: string | null
  summary: string | null
  status: string
  ip: string | null
  user_agent: string | null
  created_at: string
}

export type EntryFieldOption = {
  id: number
  field_key: 'market' | 'variety'
  value: string
  sort_order: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export type EntryFieldOptionList = {
  items: EntryFieldOption[]
  total: number
}

export type FieldConversionRule = {
  id: number
  field_key: 'grade'
  source_value: string
  target_value: string
  sort_order: number
  is_active: boolean
  description: string | null
  created_at: string
  updated_at: string
}

export type FieldConversionRuleList = {
  items: FieldConversionRule[]
  total: number
}
