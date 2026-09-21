<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { del, get, patch, post } from '../api/client'
import { confirmAction, notify } from '../feedback'
import { hasPermission } from '../auth'
import { useEscapeClose } from '../composables/useEscapeClose'
import KeyRound from '@lucide/vue/dist/esm/icons/key-round.mjs'
import LogOut from '@lucide/vue/dist/esm/icons/log-out.mjs'
import Pencil from '@lucide/vue/dist/esm/icons/pencil.mjs'
import Power from '@lucide/vue/dist/esm/icons/power.mjs'
import Trash2 from '@lucide/vue/dist/esm/icons/trash.mjs'
import DataTable, { type DataTableColumn } from '../components/DataTable.vue'
import PaginationBar from '../components/PaginationBar.vue'
import type { ListResponse, RoleItem, UserItem } from '../types'

const items = ref<UserItem[]>([])
const total = ref(0)
const roles = ref<RoleItem[]>([])
const page = ref(1)
const pageSize = ref(10)
const keyword = ref('')
const roleFilter = ref<number | ''>('')
const activeFilter = ref<'' | 'true' | 'false'>('')
const loading = ref(false)
const error = ref('')
const showModal = ref(false)
const editingId = ref<number | null>(null)
const selectedRoleIds = ref<number[]>([])
const form = reactive({ display_name: '', password: '', is_active: true })
const showPasswordModal = ref(false)
const passwordTarget = ref<UserItem | null>(null)
const newPassword = ref('')
const saving = ref(false)
const busyUserId = ref<number | null>(null)

/** 用户列表列固定，角色 / 状态 / 操作走插槽渲染。 */
const columns: DataTableColumn<UserItem>[] = [
  { key: 'id', label: 'ID', numeric: true },
  { key: 'display_name', label: '用户名', emphasis: true, rowHeader: true },
  { key: 'email', label: '邮箱', value: (user) => user.email || '—' },
  { key: 'roles', label: '角色' },
  { key: 'is_active', label: '状态' },
  { key: 'last_login_at', label: '最后登录', value: (user) => (user.last_login_at ? new Date(user.last_login_at).toLocaleString() : '—') },
  { key: 'created_at', label: '创建时间', value: (user) => new Date(user.created_at).toLocaleString() },
  { key: 'actions', label: '操作' },
]

useEscapeClose(() => showPasswordModal.value, () => {
  showPasswordModal.value = false
})
useEscapeClose(() => !showPasswordModal.value && showModal.value, () => {
  showModal.value = false
})

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

async function load() {
  loading.value = true
  error.value = ''
  try {
    const params = new URLSearchParams({
      page: String(page.value),
      page_size: String(pageSize.value),
    })
    if (keyword.value) params.set('keyword', keyword.value)
    if (roleFilter.value !== '') params.set('role_id', String(roleFilter.value))
    if (activeFilter.value !== '') params.set('is_active', activeFilter.value)
    const data = await get<ListResponse<UserItem>>(`/api/admin/users?${params}`)
    items.value = data.items
    total.value = data.total
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function loadRoles() {
  try {
    const data = await get<ListResponse<RoleItem>>('/api/admin/roles')
    roles.value = data.items
  } catch {
    roles.value = []
  }
}

function openCreate() {
  editingId.value = null
  form.display_name = ''
  form.password = ''
  form.is_active = true
  selectedRoleIds.value = []
  showModal.value = true
}

function openEdit(user: UserItem) {
  editingId.value = user.id
  form.display_name = user.display_name
  form.password = ''
  form.is_active = user.is_active
  selectedRoleIds.value = user.roles.map((role) => role.id)
  showModal.value = true
}

async function save() {
  saving.value = true
  try {
    if (editingId.value === null) {
      await post('/api/admin/users', {
        display_name: form.display_name,
        password: form.password,
        is_active: form.is_active,
        role_ids: selectedRoleIds.value,
      })
      notify('用户已创建')
    } else {
      await patch(`/api/admin/users/${editingId.value}`, {
        display_name: form.display_name,
        is_active: form.is_active,
        role_ids: selectedRoleIds.value,
      })
      notify('用户信息已更新')
    }
    showModal.value = false
    await load()
  } catch (err) {
    notify(err instanceof Error ? err.message : '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

function openResetPassword(user: UserItem) {
  passwordTarget.value = user
  newPassword.value = ''
  showPasswordModal.value = true
}

async function savePassword() {
  if (!passwordTarget.value || newPassword.value.length < 8) {
    notify('新密码至少需要 8 位', 'error')
    return
  }
  saving.value = true
  try {
    await post(`/api/admin/users/${passwordTarget.value.id}/reset-password`, {
      password: newPassword.value,
    })
    notify('密码已重置，该用户已强制下线')
    showPasswordModal.value = false
  } catch (err) {
    notify(err instanceof Error ? err.message : '重置密码失败', 'error')
  } finally {
    saving.value = false
  }
}

async function toggleActive(user: UserItem) {
  busyUserId.value = user.id
  try {
    await patch(`/api/admin/users/${user.id}`, { is_active: !user.is_active })
    notify(user.is_active ? '用户已禁用' : '用户已启用')
    await load()
  } catch (err) {
    notify(err instanceof Error ? err.message : '状态更新失败', 'error')
  } finally {
    busyUserId.value = null
  }
}

async function forceLogout(user: UserItem) {
  const ok = await confirmAction(`确认强制下线用户 ${user.display_name}？`, {
    title: '强制下线',
    confirmText: '强制下线',
  })
  if (!ok) return
  busyUserId.value = user.id
  try {
    await post(`/api/admin/users/${user.id}/force-logout`)
    notify('该用户已强制下线')
  } catch (err) {
    notify(err instanceof Error ? err.message : '操作失败', 'error')
  } finally {
    busyUserId.value = null
  }
}

async function removeUser(user: UserItem) {
  const ok = await confirmAction(`确认删除用户 ${user.display_name}？此操作不可恢复。`, {
    title: '删除用户',
    confirmText: '删除',
  })
  if (!ok) return
  busyUserId.value = user.id
  try {
    await del(`/api/admin/users/${user.id}`)
    notify('用户已删除')
    await load()
  } catch (err) {
    notify(err instanceof Error ? err.message : '删除失败', 'error')
  } finally {
    busyUserId.value = null
  }
}

onMounted(async () => {
  await Promise.all([load(), loadRoles()])
})
</script>

<template>
  <section class="page-stack">
    <div class="list-card">
      <div class="toolbar">
        <input v-model="keyword" class="input" style="max-width: 220px" placeholder="搜索用户名" @keyup.enter="page = 1; load()" />
        <select v-model="roleFilter" class="select" style="max-width: 180px" @change="page = 1; load()">
          <option value="">全部角色</option>
          <option v-for="role in roles" :key="role.id" :value="role.id">{{ role.name }}</option>
        </select>
        <select v-model="activeFilter" class="select" style="max-width: 140px" @change="page = 1; load()">
          <option value="">全部状态</option>
          <option value="true">启用</option>
          <option value="false">禁用</option>
        </select>
        <button class="secondary-button" @click="page = 1; load()">查询</button>
        <button v-if="hasPermission('admin:user:create')" class="primary-button toolbar-action" @click="openCreate">新增用户</button>
      </div>

    <p v-if="error" class="error">{{ error }}</p>

    <DataTable
      class="fixed-height-list"
      :columns="columns"
      :rows="items"
      :row-key="(user) => user.id"
      caption="管理端用户列表"
      min-width="880px"
      :empty-text="loading ? '正在加载…' : '暂无用户'"
    >
      <template #cell-roles="{ row }">
        <span v-for="role in row.roles" :key="role.id" class="tag" style="margin-right: 4px">{{ role.name }}</span>
      </template>
      <template #cell-is_active="{ row }">
        <span class="tag" :class="row.is_active ? 'success' : 'danger'">{{ row.is_active ? '启用' : '禁用' }}</span>
      </template>
      <template #cell-actions="{ row }">
        <div class="table-actions">
          <button v-if="hasPermission('admin:user:update')" class="table-action" :disabled="busyUserId === row.id" @click="openEdit(row)"><Pencil :size="15" :stroke-width="2" aria-hidden="true" />编辑</button>
          <button v-if="hasPermission('admin:user:reset-password')" class="table-action" :disabled="busyUserId === row.id" @click="openResetPassword(row)"><KeyRound :size="15" :stroke-width="2" aria-hidden="true" />重置密码</button>
          <button v-if="hasPermission('admin:user:update')" class="table-action" :disabled="busyUserId === row.id" @click="forceLogout(row)"><LogOut :size="15" :stroke-width="2" aria-hidden="true" />强制下线</button>
          <button v-if="hasPermission('admin:user:disable')" class="table-action" :disabled="busyUserId === row.id" @click="toggleActive(row)"><Power :size="15" :stroke-width="2" aria-hidden="true" />{{ row.is_active ? '禁用' : '启用' }}</button>
          <button v-if="hasPermission('admin:user:delete')" class="table-action danger" :disabled="busyUserId === row.id" @click="removeUser(row)"><Trash2 :size="15" :stroke-width="2" aria-hidden="true" />删除</button>
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
      <div class="drawer" role="dialog" aria-modal="true" aria-label="用户编辑">
        <div class="drawer-header">
          <div class="drawer-title">{{ editingId === null ? '新增用户' : '编辑用户' }}</div>
          <button class="link-button" @click="showModal = false">关闭</button>
        </div>
        <div class="drawer-body">
        <div class="field">
          <label>用户名</label>
          <input v-model="form.display_name" class="input" />
        </div>
        <div v-if="editingId === null" class="field">
          <label>初始密码</label>
          <input v-model="form.password" class="input" type="password" minlength="8" />
        </div>
        <div class="field checkbox-row">
          <input id="user-active" v-model="form.is_active" type="checkbox" />
          <label for="user-active">启用账号</label>
        </div>
        <div class="field">
          <label>角色</label>
          <label v-for="role in roles" :key="role.id" class="checkbox-row">
            <input v-model="selectedRoleIds" type="checkbox" :value="role.id" />
            {{ role.name }}
          </label>
        </div>
        </div>
        <div class="drawer-actions">
          <button class="secondary-button" @click="showModal = false">取消</button>
          <button class="primary-button" :disabled="saving" @click="save">{{ saving ? '保存中...' : '保存' }}</button>
        </div>
      </div>
    </div>

    <div v-if="showPasswordModal" class="modal-mask">
      <div class="modal">
        <div class="modal-header">
          <div class="modal-title">重置密码：{{ passwordTarget?.display_name }}</div>
          <button class="link-button" @click="showPasswordModal = false">关闭</button>
        </div>
        <div class="field">
          <label>新密码（至少 8 位）</label>
          <input v-model="newPassword" class="input" type="password" minlength="8" />
        </div>
        <div class="modal-actions">
          <button class="secondary-button" @click="showPasswordModal = false">取消</button>
          <button class="primary-button" :disabled="saving" @click="savePassword">{{ saving ? '提交中...' : '重置并强制下线' }}</button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.danger-text { color: var(--danger); }
.fixed-height-list {
  height: 31rem;
  min-height: 31rem;
  overflow-y: hidden;
}

@media (max-width: 820px) {
  .fixed-height-list {
    height: auto;
    min-height: 24rem;
  }
}
</style>
