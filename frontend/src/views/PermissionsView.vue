<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { del, get, patch, post } from '../api/client'
import { confirmAction, notify } from '../feedback'
import { hasPermission } from '../auth'
import { useEscapeClose } from '../composables/useEscapeClose'
import DataTable, { type DataTableColumn } from '../components/DataTable.vue'
import Pencil from '@lucide/vue/dist/esm/icons/pencil.mjs'
import Trash2 from '@lucide/vue/dist/esm/icons/trash.mjs'
import type { ListResponse, PermissionItem } from '../types'

const items = ref<PermissionItem[]>([])
const keyword = ref('')
const moduleFilter = ref('')
const error = ref('')
const saving = ref(false)
const busyId = ref<number | null>(null)
const showModal = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({
  code: '',
  name: '',
  module: 'overview',
  permission_type: 'action' as 'menu' | 'action' | 'api' | 'data',
  description: '',
  is_active: true,
})

/** 权限点列表列固定，编码 / 状态 / 操作走插槽渲染。 */
const columns: DataTableColumn<PermissionItem>[] = [
  { key: 'id', label: 'ID', numeric: true },
  { key: 'code', label: '编码', emphasis: true, rowHeader: true },
  { key: 'name', label: '名称' },
  { key: 'module', label: '模块' },
  { key: 'permission_type', label: '类型' },
  { key: 'is_active', label: '状态' },
  { key: 'description', label: '说明', value: (item) => item.description || '—' },
  { key: 'actions', label: '操作' },
]

useEscapeClose(() => showModal.value, () => {
  showModal.value = false
})

async function load() {
  error.value = ''
  try {
    const params = new URLSearchParams()
    if (keyword.value) params.set('keyword', keyword.value)
    if (moduleFilter.value) params.set('module', moduleFilter.value)
    const data = await get<ListResponse<PermissionItem>>(`/api/admin/permissions?${params}`)
    items.value = data.items
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败'
  }
}

function openCreate() {
  editingId.value = null
  Object.assign(form, {
    code: '',
    name: '',
    module: 'overview',
    permission_type: 'action',
    description: '',
    is_active: true,
  })
  showModal.value = true
}

function openEdit(item: PermissionItem) {
  editingId.value = item.id
  Object.assign(form, {
    code: item.code,
    name: item.name,
    module: item.module,
    permission_type: item.permission_type,
    description: item.description || '',
    is_active: item.is_active,
  })
  showModal.value = true
}

async function save() {
  saving.value = true
  try {
    const payload = { ...form, code: form.code }
    if (editingId.value === null) {
      await post('/api/admin/permissions', payload)
      notify('权限点已创建')
    } else {
      await patch(`/api/admin/permissions/${editingId.value}`, {
        name: form.name,
        module: form.module,
        permission_type: form.permission_type,
        description: form.description,
        is_active: form.is_active,
      })
      notify('权限点已更新')
    }
    showModal.value = false
    await load()
  } catch (err) {
    notify(err instanceof Error ? err.message : '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

async function removePermission(item: PermissionItem) {
  const ok = await confirmAction(`确认删除权限点 ${item.code}？已授权角色会同步失去该权限。`, {
    title: '删除权限点',
    confirmText: '删除',
  })
  if (!ok) return
  busyId.value = item.id
  try {
    await del(`/api/admin/permissions/${item.id}`)
    notify('权限点已删除')
    await load()
  } catch (err) {
    notify(err instanceof Error ? err.message : '删除失败', 'error')
  } finally {
    busyId.value = null
  }
}

onMounted(load)
</script>

<template>
  <section class="page-stack">
    <div class="list-card">
      <div class="toolbar">
        <input v-model="keyword" class="input" style="max-width: 220px" placeholder="搜索编码或名称" @keyup.enter="load" />
        <select v-model="moduleFilter" class="select" style="max-width: 160px" @change="load">
          <option value="">全部模块</option>
          <option value="overview">overview</option>
          <option value="settlement">settlement</option>
          <option value="series">series</option>
          <option value="import">import</option>
          <option value="data">data</option>
          <option value="ai">ai</option>
          <option value="preview">preview</option>
        </select>
        <button class="secondary-button" @click="load">查询</button>
        <button v-if="hasPermission('admin:permission:create')" class="primary-button toolbar-action" @click="openCreate">新增权限点</button>
      </div>

    <p v-if="error" class="error">{{ error }}</p>

    <DataTable
      :columns="columns"
      :rows="items"
      :row-key="(item) => item.id"
      caption="管理端权限点列表"
      min-width="900px"
      empty-text="暂无权限点"
    >
      <template #cell-code="{ row }">
        <code>{{ row.code }}</code>
      </template>
      <template #cell-is_active="{ row }">
        <span class="tag" :class="row.is_active ? 'success' : 'danger'">{{ row.is_active ? '启用' : '停用' }}</span>
      </template>
      <template #cell-actions="{ row }">
        <div class="table-actions">
          <button v-if="hasPermission('admin:permission:update')" class="table-action" :disabled="busyId === row.id" @click="openEdit(row)"><Pencil :size="15" :stroke-width="2" aria-hidden="true" />编辑</button>
          <button v-if="hasPermission('admin:permission:delete')" class="table-action danger" :disabled="busyId === row.id" @click="removePermission(row)"><Trash2 :size="15" :stroke-width="2" aria-hidden="true" />删除</button>
        </div>
      </template>
    </DataTable>
    </div>

    <div v-if="showModal" class="drawer-mask" @click.self="showModal = false">
      <div class="drawer" role="dialog" aria-modal="true" aria-label="权限点编辑">
        <div class="drawer-header">
          <div class="drawer-title">{{ editingId === null ? '新增权限点' : '编辑权限点' }}</div>
          <button class="link-button" @click="showModal = false">关闭</button>
        </div>
        <div class="drawer-body">
        <div class="field">
          <label>权限编码</label>
          <input v-model="form.code" class="input" :disabled="editingId !== null" placeholder="import:upload" />
        </div>
        <div class="field">
          <label>权限名称</label>
          <input v-model="form.name" class="input" />
        </div>
        <div class="field">
          <label>模块</label>
          <input v-model="form.module" class="input" />
        </div>
        <div class="field">
          <label>类型</label>
          <select v-model="form.permission_type" class="select">
            <option value="menu">menu</option>
            <option value="action">action</option>
            <option value="api">api</option>
            <option value="data">data</option>
          </select>
        </div>
        <div class="field">
          <label>说明</label>
          <textarea v-model="form.description" class="textarea"></textarea>
        </div>
        <div class="field checkbox-row">
          <input id="permission-active" v-model="form.is_active" type="checkbox" />
          <label for="permission-active">启用权限点</label>
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
.danger-text { color: var(--danger); }
</style>
