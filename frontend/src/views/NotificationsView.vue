<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { del, get, patch, post } from '../api/client'
import { confirmAction, notify } from '../feedback'
import { hasPermission } from '../auth'
import { useEscapeClose } from '../composables/useEscapeClose'
import Pencil from '@lucide/vue/dist/esm/icons/pencil.mjs'
import Send from '@lucide/vue/dist/esm/icons/send.mjs'
import Trash2 from '@lucide/vue/dist/esm/icons/trash.mjs'
import DataTable, { type DataTableColumn } from '../components/DataTable.vue'
import RichTextEditor from '../components/RichTextEditor.vue'
import PaginationBar from '../components/PaginationBar.vue'
import { notificationPlainText, sanitizeNotificationHtml } from '../notificationHtml'
import type { ListResponse, NotificationItem, RoleItem, UserItem } from '../types'

const items = ref<NotificationItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const keyword = ref('')
const typeFilter = ref('')
const priorityFilter = ref('')
const statusFilter = ref<'' | 'true' | 'false'>('')
const loading = ref(false)
const error = ref('')
const roles = ref<RoleItem[]>([])
const users = ref<UserItem[]>([])
const showModal = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const busyId = ref<number | null>(null)
const form = reactive({
  title: '',
  content: '',
  notification_type: 'announcement',
  priority: 'normal',
  target_type: 'all',
  target_role_ids: [] as number[],
  target_user_ids: [] as number[],
  is_published: false,
  publish_at: '',
  expire_at: '',
})

/** 通知列表列固定，标题 / 类型 / 优先级 / 状态 / 操作走插槽渲染。 */
const columns: DataTableColumn<NotificationItem>[] = [
  { key: 'id', label: 'ID', numeric: true },
  { key: 'title', label: '标题', emphasis: true, rowHeader: true },
  { key: 'notification_type', label: '类型' },
  { key: 'priority', label: '优先级' },
  { key: 'target', label: '范围' },
  { key: 'read', label: '阅读进度' },
  { key: 'is_published', label: '状态' },
  { key: 'publish_at', label: '发布时间', value: (item) => (item.publish_at ? new Date(item.publish_at).toLocaleString() : '—') },
  { key: 'actions', label: '操作' },
]

const targetLabel = (item: NotificationItem) => {
  if (item.target_type === 'all') return '全部用户'
  if (item.target_type === 'role') return `${item.target_role_ids.length} 个角色`
  return `${item.target_user_ids.length} 个用户`
}

const priorityTone = (priority: string) => (priority === 'normal' ? '' : priority === 'important' ? 'warning' : 'danger')

useEscapeClose(() => showModal.value, () => {
  showModal.value = false
})

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))
const typeLabels: Record<string, string> = {
  announcement: '公告',
  task: '任务',
  system: '系统',
}
const priorityLabels: Record<string, string> = {
  normal: '普通',
  important: '重要',
  urgent: '紧急',
}

function toLocalInput(value: string | null) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const offset = date.getTimezoneOffset() * 60000
  return new Date(date.getTime() - offset).toISOString().slice(0, 16)
}

function toIso(value: string) {
  return value ? new Date(value).toISOString() : null
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const params = new URLSearchParams({ page: String(page.value), page_size: String(pageSize.value) })
    if (keyword.value) params.set('keyword', keyword.value)
    if (typeFilter.value) params.set('notification_type', typeFilter.value)
    if (priorityFilter.value) params.set('priority', priorityFilter.value)
    if (statusFilter.value !== '') params.set('is_published', statusFilter.value)
    const data = await get<ListResponse<NotificationItem>>(`/api/admin/notifications?${params}`)
    items.value = data.items
    total.value = data.total
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function loadMeta() {
  const [roleData, userData] = await Promise.all([
    get<ListResponse<RoleItem>>('/api/admin/roles'),
    get<ListResponse<UserItem>>('/api/admin/users?page_size=100'),
  ])
  roles.value = roleData.items
  users.value = userData.items.filter((item) => item.is_active)
}

function openCreate() {
  editingId.value = null
  form.title = ''
  form.content = ''
  form.notification_type = 'announcement'
  form.priority = 'normal'
  form.target_type = 'all'
  form.target_role_ids = []
  form.target_user_ids = []
  form.is_published = false
  form.publish_at = ''
  form.expire_at = ''
  showModal.value = true
}

function openEdit(item: NotificationItem) {
  editingId.value = item.id
  form.title = item.title
  form.content = item.content
  form.notification_type = item.notification_type
  form.priority = item.priority
  form.target_type = item.target_type
  form.target_role_ids = [...item.target_role_ids]
  form.target_user_ids = [...item.target_user_ids]
  form.is_published = item.is_published
  form.publish_at = toLocalInput(item.publish_at)
  form.expire_at = toLocalInput(item.expire_at)
  showModal.value = true
}

async function save() {
  const sanitizedContent = sanitizeNotificationHtml(form.content)
  if (!form.title.trim() || !notificationPlainText(sanitizedContent)) {
    notify('标题和内容不能为空', 'error')
    return
  }
  if ((form.target_type === 'role' && !form.target_role_ids.length) || (form.target_type === 'user' && !form.target_user_ids.length)) {
    notify('请选择通知接收对象', 'error')
    return
  }
  saving.value = true
  const payload = {
    title: form.title.trim(),
    content: sanitizedContent,
    notification_type: form.notification_type,
    priority: form.priority,
    target_type: form.target_type,
    target_role_ids: form.target_type === 'role' ? form.target_role_ids : [],
    target_user_ids: form.target_type === 'user' ? form.target_user_ids : [],
    is_published: form.is_published,
    publish_at: toIso(form.publish_at),
    expire_at: toIso(form.expire_at),
  }
  try {
    if (editingId.value === null) {
      await post('/api/admin/notifications', payload)
      notify('通知已创建')
    } else {
      await patch(`/api/admin/notifications/${editingId.value}`, payload)
      notify('通知已更新')
    }
    showModal.value = false
    await load()
  } catch (err) {
    notify(err instanceof Error ? err.message : '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

async function publish(item: NotificationItem) {
  busyId.value = item.id
  try {
    await post(`/api/admin/notifications/${item.id}/publish`)
    notify('通知已发布')
    await load()
  } catch (err) {
    notify(err instanceof Error ? err.message : '发布失败', 'error')
  } finally {
    busyId.value = null
  }
}

async function removeItem(item: NotificationItem) {
  const ok = await confirmAction(`确认删除通知「${item.title}」？此操作不可恢复。`, {
    title: '删除通知',
    confirmText: '删除',
  })
  if (!ok) return
  busyId.value = item.id
  try {
    await del(`/api/admin/notifications/${item.id}`)
    notify('通知已删除')
    await load()
  } catch (err) {
    notify(err instanceof Error ? err.message : '删除失败', 'error')
  } finally {
    busyId.value = null
  }
}

onMounted(async () => {
  await Promise.all([load(), loadMeta()])
})
</script>

<template>
  <section class="page-stack">
    <div class="list-card">
      <div class="toolbar">
        <input v-model="keyword" class="input" style="max-width: 220px" placeholder="标题/内容" @keyup.enter="page = 1; load()" />
        <select v-model="typeFilter" class="select" style="max-width: 130px" @change="page = 1; load()">
          <option value="">全部类型</option>
          <option value="announcement">公告</option>
          <option value="task">任务</option>
          <option value="system">系统</option>
        </select>
        <select v-model="priorityFilter" class="select" style="max-width: 130px" @change="page = 1; load()">
          <option value="">全部优先级</option>
          <option value="normal">普通</option>
          <option value="important">重要</option>
          <option value="urgent">紧急</option>
        </select>
        <select v-model="statusFilter" class="select" style="max-width: 130px" @change="page = 1; load()">
          <option value="">全部状态</option>
          <option value="true">已发布</option>
          <option value="false">草稿</option>
        </select>
        <button class="secondary-button" @click="page = 1; load()">查询</button>
        <button v-if="hasPermission('admin:notification:create')" class="primary-button toolbar-action" @click="openCreate">新建通知</button>
      </div>

    <p v-if="error" class="error">{{ error }}</p>

    <DataTable
      :columns="columns"
      :rows="items"
      :row-key="(item) => item.id"
      caption="管理端通知列表"
      min-width="1080px"
      :empty-text="loading ? '正在加载…' : '暂无通知'"
    >
      <template #cell-title="{ row }">
        <span class="notification-title-cell">{{ row.title }}</span>
      </template>
      <template #cell-notification_type="{ row }">
        <span class="tag">{{ typeLabels[row.notification_type] || row.notification_type }}</span>
      </template>
      <template #cell-priority="{ row }">
        <span class="tag" :class="priorityTone(row.priority)">{{ priorityLabels[row.priority] }}</span>
      </template>
      <template #cell-target="{ row }">
        {{ targetLabel(row) }}
      </template>
      <template #cell-read="{ row }">
        {{ row.read_count }} / {{ row.recipient_total }}
      </template>
      <template #cell-is_published="{ row }">
        <span class="tag" :class="row.is_published ? 'success' : ''">{{ row.is_published ? '已发布' : '草稿' }}</span>
      </template>
      <template #cell-actions="{ row }">
        <div class="table-actions">
          <button v-if="!row.is_published && hasPermission('admin:notification:publish')" class="table-action" :disabled="busyId === row.id" @click="publish(row)"><Send :size="15" :stroke-width="2" aria-hidden="true" />发布</button>
          <button v-if="hasPermission('admin:notification:update')" class="table-action" :disabled="busyId === row.id" @click="openEdit(row)"><Pencil :size="15" :stroke-width="2" aria-hidden="true" />编辑</button>
          <button v-if="hasPermission('admin:notification:delete')" class="table-action danger" :disabled="busyId === row.id" @click="removeItem(row)"><Trash2 :size="15" :stroke-width="2" aria-hidden="true" />删除</button>
        </div>
      </template>
      <template #footer>
        <PaginationBar
          v-model:page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-size-options="[10, 20, 50, 100]"
          @change="load"
        />
      </template>
    </DataTable>
    </div>

    <div v-if="showModal" class="drawer-mask" @click.self="showModal = false">
      <div class="drawer notification-drawer" role="dialog" aria-modal="true" aria-label="通知编辑">
        <div class="drawer-header">
          <div class="drawer-title">{{ editingId === null ? '新建通知' : '编辑通知' }}</div>
          <button class="link-button" @click="showModal = false">关闭</button>
        </div>
        <div class="drawer-body">
          <div class="field">
            <label>标题</label>
            <input v-model="form.title" class="input" maxlength="160" />
          </div>
          <div class="field">
            <label>内容</label>
            <RichTextEditor v-model="form.content" />
          </div>
          <div class="field-grid">
            <div class="field">
              <label>类型</label>
              <select v-model="form.notification_type" class="select">
                <option value="announcement">公告</option>
                <option value="task">任务</option>
                <option value="system">系统</option>
              </select>
            </div>
            <div class="field">
              <label>优先级</label>
              <select v-model="form.priority" class="select">
                <option value="normal">普通</option>
                <option value="important">重要</option>
                <option value="urgent">紧急</option>
              </select>
            </div>
          </div>
          <div class="field">
            <label>发送范围</label>
            <select v-model="form.target_type" class="select">
              <option value="all">全部用户</option>
              <option value="role">指定角色</option>
              <option value="user">指定用户</option>
            </select>
          </div>
          <div v-if="form.target_type === 'role'" class="field">
            <label>接收角色</label>
            <label v-for="role in roles" :key="role.id" class="checkbox-row">
              <input v-model="form.target_role_ids" type="checkbox" :value="role.id" />
              {{ role.name }}
            </label>
          </div>
          <div v-if="form.target_type === 'user'" class="field">
            <label>接收用户</label>
            <select v-model="form.target_user_ids" class="select" multiple>
              <option v-for="user in users" :key="user.id" :value="user.id">{{ user.display_name }}</option>
            </select>
          </div>
          <div class="field checkbox-row">
            <input id="notification-published" v-model="form.is_published" type="checkbox" />
            <label for="notification-published">创建后立即发布</label>
          </div>
          <div class="field-grid">
            <div class="field">
              <label>定时发布时间</label>
              <input v-model="form.publish_at" class="input" type="datetime-local" />
            </div>
            <div class="field">
              <label>失效时间</label>
              <input v-model="form.expire_at" class="input" type="datetime-local" />
            </div>
          </div>
        </div>
        <div class="drawer-actions">
          <button class="secondary-button" @click="showModal = false">取消</button>
          <button class="primary-button" :disabled="saving" @click="save">{{ saving ? '保存中...' : '保存' }}</button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}
.notification-title-cell {
  display: inline-block;
  max-width: 18rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tag.warning {
  border-color: var(--warning);
  background: #fff6e4;
  color: #7a4d08;
}
@media (max-width: 620px) {
  .field-grid { grid-template-columns: 1fr; }
}
</style>
