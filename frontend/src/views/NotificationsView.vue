<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { del, get, patch, post } from '../api/client'
import { confirmAction, notify } from '../feedback'
import { hasPermission } from '../auth'
import Pencil from '@lucide/vue/dist/esm/icons/pencil.mjs'
import Send from '@lucide/vue/dist/esm/icons/send.mjs'
import Trash2 from '@lucide/vue/dist/esm/icons/trash.mjs'
import RichTextEditor from '../components/RichTextEditor.vue'
import PaginationBar from '../components/PaginationBar.vue'
import { notificationPlainText, sanitizeNotificationHtml } from '../notificationHtml'
import type { ListResponse, NotificationItem, RoleItem, UserItem } from '../types'

const items = ref<NotificationItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
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

    <div class="table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>标题</th>
            <th>类型</th>
            <th>优先级</th>
            <th>范围</th>
            <th>阅读进度</th>
            <th>状态</th>
            <th>发布时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.id">
            <td>{{ item.id }}</td>
            <td class="notification-title-cell">{{ item.title }}</td>
            <td><span class="tag">{{ typeLabels[item.notification_type] || item.notification_type }}</span></td>
            <td><span class="tag" :class="item.priority === 'normal' ? '' : item.priority === 'important' ? 'warning' : 'danger'">{{ priorityLabels[item.priority] }}</span></td>
            <td>{{ item.target_type === 'all' ? '全部用户' : item.target_type === 'role' ? `${item.target_role_ids.length} 个角色` : `${item.target_user_ids.length} 个用户` }}</td>
            <td>{{ item.read_count }} / {{ item.recipient_total }}</td>
            <td><span class="tag" :class="item.is_published ? 'success' : ''">{{ item.is_published ? '已发布' : '草稿' }}</span></td>
            <td>{{ item.publish_at ? new Date(item.publish_at).toLocaleString() : '—' }}</td>
            <td>
              <div class="table-actions">
                <button v-if="!item.is_published && hasPermission('admin:notification:publish')" class="table-action" :disabled="busyId === item.id" @click="publish(item)"><Send :size="15" :stroke-width="2" aria-hidden="true" />发布</button>
                <button v-if="hasPermission('admin:notification:update')" class="table-action" :disabled="busyId === item.id" @click="openEdit(item)"><Pencil :size="15" :stroke-width="2" aria-hidden="true" />编辑</button>
                <button v-if="hasPermission('admin:notification:delete')" class="table-action danger" :disabled="busyId === item.id" @click="removeItem(item)"><Trash2 :size="15" :stroke-width="2" aria-hidden="true" />删除</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-if="!loading && !items.length" class="empty-state">暂无通知</div>

      <PaginationBar
        v-model:page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-size-options="[10, 20, 50, 100]"
        @change="load"
      />
    </div>

    <div v-if="showModal" class="modal-mask">
      <div class="modal notification-modal">
        <div class="modal-header">
          <div class="modal-title">{{ editingId === null ? '新建通知' : '编辑通知' }}</div>
          <button class="link-button" @click="showModal = false">关闭</button>
        </div>
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
        <div class="modal-actions">
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
