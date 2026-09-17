<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { del, get, patch, post, put } from '../api/client'
import { confirmAction, notify } from '../feedback'
import { hasPermission } from '../auth'
import DataTable, { type DataTableColumn } from '../components/DataTable.vue'
import GrantMenuTreeNode from '../components/GrantMenuTreeNode.vue'
import { useEscapeClose } from '../composables/useEscapeClose'
import Pencil from '@lucide/vue/dist/esm/icons/pencil.mjs'
import ShieldCheck from '@lucide/vue/dist/esm/icons/shield-check.mjs'
import Trash2 from '@lucide/vue/dist/esm/icons/trash.mjs'
import type { ListResponse, MenuNode, PermissionItem, RoleItem } from '../types'

const roles = ref<RoleItem[]>([])
const menus = ref<MenuNode[]>([])
const permissions = ref<PermissionItem[]>([])
const error = ref('')
const showModal = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({ code: '', name: '', description: '', is_active: true })
const showGrantModal = ref(false)
const grantRole = ref<RoleItem | null>(null)
const selectedMenuIds = ref<number[]>([])
const selectedPermissionIds = ref<number[]>([])
const saving = ref(false)
const busyRoleId = ref<number | null>(null)
const metaError = ref('')
// 授权抽屉：菜单 / 权限点用标签页切换，避免两段长列表上下堆叠
const grantTab = ref<'menu' | 'permission'>('menu')

/** 角色列表列固定，名称 / 状态 / 操作走插槽渲染。 */
const columns: DataTableColumn<RoleItem>[] = [
  { key: 'id', label: 'ID', numeric: true },
  { key: 'name', label: '角色名称', emphasis: true, rowHeader: true },
  { key: 'code', label: '编码' },
  { key: 'is_active', label: '状态' },
  { key: 'user_count', label: '用户数', numeric: true },
  { key: 'menu_ids', label: '菜单数', numeric: true, value: (role) => role.menu_ids.length },
  { key: 'permission_ids', label: '权限数', numeric: true, value: (role) => role.permission_ids.length },
  { key: 'description', label: '说明', value: (role) => role.description || '—' },
  { key: 'actions', label: '操作' },
]

useEscapeClose(() => showGrantModal.value, () => {
  showGrantModal.value = false
})
useEscapeClose(() => !showGrantModal.value && showModal.value, () => {
  showModal.value = false
})

async function load() {
  error.value = ''
  try {
    const data = await get<ListResponse<RoleItem>>('/api/admin/roles')
    roles.value = data.items
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败'
  }
}

async function loadMeta() {
  try {
    const [menuData, permissionData] = await Promise.all([
      get<{ items: MenuNode[] }>('/api/admin/menus/tree'),
      get<ListResponse<PermissionItem>>('/api/admin/permissions'),
    ])
    menus.value = menuData.items
    permissions.value = permissionData.items
    metaError.value = ''
  } catch (err) {
    metaError.value = err instanceof Error ? err.message : '菜单与权限数据加载失败'
    notify(metaError.value, 'error')
  }
}

function openCreate() {
  editingId.value = null
  form.code = ''
  form.name = ''
  form.description = ''
  form.is_active = true
  showModal.value = true
}

function openEdit(role: RoleItem) {
  editingId.value = role.id
  form.code = role.code
  form.name = role.name
  form.description = role.description || ''
  form.is_active = role.is_active
  showModal.value = true
}

async function save() {
  saving.value = true
  try {
    if (editingId.value === null) {
      await post('/api/admin/roles', form)
      notify('角色已创建')
    } else {
      await patch(`/api/admin/roles/${editingId.value}`, {
        name: form.name,
        description: form.description,
        is_active: form.is_active,
      })
      notify('角色信息已更新')
    }
    showModal.value = false
    await load()
  } catch (err) {
    notify(err instanceof Error ? err.message : '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

// 系统内置角色始终拥有全部权限，后端会拒绝授权请求，这里给出明确反馈而不是静默无响应
const LOCKED_GRANT_ROLES = new Set(['super_admin', 'fruit_admin'])

function isGrantLocked(role: RoleItem) {
  return LOCKED_GRANT_ROLES.has(role.code)
}

async function openGrant(role: RoleItem) {
  if (isGrantLocked(role)) {
    notify(`「${role.name}」为系统内置角色，始终拥有全部权限，无需单独授权`, 'info')
    return
  }
  if (metaError.value) {
    notify('菜单与权限数据未加载成功，请刷新页面后重试', 'error')
    return
  }
  try {
    grantRole.value = role
    grantTab.value = 'menu'
    selectedMenuIds.value = [...(role.menu_ids || [])]
    selectedPermissionIds.value = [...(role.permission_ids || [])]
    showGrantModal.value = true
  } catch (err) {
    notify(err instanceof Error ? err.message : '打开授权面板失败', 'error')
  }
}

async function saveGrant() {
  if (!grantRole.value) return
  if (metaError.value) {
    notify('菜单与权限数据未加载成功，请刷新页面后重试', 'error')
    return
  }
  saving.value = true
  try {
    await put(`/api/admin/roles/${grantRole.value.id}/grant`, {
      menu_ids: selectedMenuIds.value,
      permission_ids: selectedPermissionIds.value,
    })
    notify('角色授权已更新')
    showGrantModal.value = false
    await load()
  } catch (err) {
    notify(err instanceof Error ? err.message : '授权保存失败', 'error')
  } finally {
    saving.value = false
  }
}

async function removeRole(role: RoleItem) {
  const ok = await confirmAction(`确认删除角色 ${role.name}？该角色下的用户将失去对应权限。`, {
    title: '删除角色',
    confirmText: '删除',
  })
  if (!ok) return
  busyRoleId.value = role.id
  try {
    await del(`/api/admin/roles/${role.id}`)
    notify('角色已删除')
    await load()
  } catch (err) {
    notify(err instanceof Error ? err.message : '删除失败', 'error')
  } finally {
    busyRoleId.value = null
  }
}

const flatMenus = computed(() => {
  const result: Array<{ id: number; name: string; depth: number }> = []
  const walk = (nodes: MenuNode[], depth = 0) => {
    for (const node of nodes) {
      result.push({ id: node.id, name: node.name, depth })
      // 接口异常时 children 可能缺失，避免计算属性抛错导致整个页面空白
      if (node.children?.length) walk(node.children, depth + 1)
    }
  }
  walk(menus.value)
  return result
})

// 勾选父级时连子级一起勾选，取消同理；整棵子树都选中才算勾选，否则父级显示半选
function collectMenuIds(node: MenuNode): number[] {
  const ids = [node.id]
  for (const child of node.children || []) ids.push(...collectMenuIds(child))
  return ids
}

function toggleMenu(node: MenuNode) {
  const ids = collectMenuIds(node)
  const allSelected = ids.every((id) => selectedMenuIds.value.includes(id))
  selectedMenuIds.value = allSelected
    ? selectedMenuIds.value.filter((id) => !ids.includes(id))
    : Array.from(new Set([...selectedMenuIds.value, ...ids]))
}

const permissionGroups = computed(() => {
  const groups = new Map<string, PermissionItem[]>()
  for (const permission of permissions.value) {
    const key = permission.module
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key)!.push(permission)
  }
  return Array.from(groups.entries()).map(([module, items]) => ({ module, items }))
})

function togglePermissionGroup(module: string, checked: boolean) {
  const ids = permissions.value.filter((item) => item.module === module).map((item) => item.id)
  selectedPermissionIds.value = checked
    ? Array.from(new Set([...selectedPermissionIds.value, ...ids]))
    : selectedPermissionIds.value.filter((id) => !ids.includes(id))
}

onMounted(async () => {
  await Promise.all([load(), loadMeta()])
})
</script>

<template>
  <section class="page-stack">
    <div class="list-card">
      <div class="toolbar">
        <span class="toolbar-summary">共 {{ roles.length }} 个角色</span>
        <button v-if="hasPermission('admin:role:create')" class="primary-button toolbar-action" @click="openCreate">新增角色</button>
      </div>
      <p v-if="error" class="error">{{ error }}</p>

    <DataTable
      :columns="columns"
      :rows="roles"
      :row-key="(role) => role.id"
      caption="管理端角色列表"
      min-width="980px"
      empty-text="暂无角色"
    >
      <template #cell-name="{ row }">
        {{ row.name }} <span v-if="row.is_system" class="tag">系统</span>
      </template>
      <template #cell-is_active="{ row }">
        <span class="tag" :class="row.is_active ? 'success' : 'danger'">{{ row.is_active ? '启用' : '停用' }}</span>
      </template>
      <template #cell-actions="{ row }">
        <div class="table-actions">
          <button v-if="hasPermission('admin:role:update')" class="table-action" :disabled="busyRoleId === row.id" @click="openEdit(row)"><Pencil :size="15" :stroke-width="2" aria-hidden="true" />编辑</button>
          <button v-if="hasPermission('admin:role:grant')" class="table-action" :class="{ 'locked-action': isGrantLocked(row) }" :disabled="busyRoleId === row.id" :title="isGrantLocked(row) ? '系统内置角色始终拥有全部权限，无需单独授权' : undefined" @click="openGrant(row)"><ShieldCheck :size="15" :stroke-width="2" aria-hidden="true" />授权</button>
          <button v-if="hasPermission('admin:role:delete') && !row.is_system" class="table-action danger" :disabled="busyRoleId === row.id" @click="removeRole(row)"><Trash2 :size="15" :stroke-width="2" aria-hidden="true" />删除</button>
        </div>
      </template>
    </DataTable>
    </div>

    <div v-if="showModal" class="drawer-mask" @click.self="showModal = false">
      <div class="drawer" role="dialog" aria-modal="true" aria-label="角色编辑">
        <div class="drawer-header">
          <div class="drawer-title">{{ editingId === null ? '新增角色' : '编辑角色' }}</div>
          <button class="link-button" @click="showModal = false">关闭</button>
        </div>
        <div class="drawer-body">
        <div class="field">
          <label>角色编码</label>
          <input v-model="form.code" class="input" :disabled="editingId !== null" />
        </div>
        <div class="field">
          <label>角色名称</label>
          <input v-model="form.name" class="input" />
        </div>
        <div class="field">
          <label>说明</label>
          <textarea v-model="form.description" class="textarea"></textarea>
        </div>
        <div class="field checkbox-row">
          <input id="role-active" v-model="form.is_active" type="checkbox" />
          <label for="role-active">启用角色</label>
        </div>
        </div>
        <div class="drawer-actions">
          <button class="secondary-button" @click="showModal = false">取消</button>
          <button class="primary-button" :disabled="saving" @click="save">{{ saving ? '保存中...' : '保存' }}</button>
        </div>
      </div>
    </div>

    <div v-if="showGrantModal && grantRole" class="drawer-mask" @click.self="showGrantModal = false">
      <div class="drawer" role="dialog" aria-modal="true" aria-label="分配角色权限">
        <div class="drawer-header">
          <div class="drawer-title">分配角色权限：{{ grantRole.name }}</div>
          <button class="link-button" @click="showGrantModal = false">关闭</button>
        </div>
        <div class="drawer-body">
          <div class="tabs grant-tabs" role="tablist">
            <button role="tab" :aria-selected="grantTab === 'menu'" :class="{ active: grantTab === 'menu' }" @click="grantTab = 'menu'">
              菜单（{{ selectedMenuIds.length }}/{{ flatMenus.length }}）
            </button>
            <button role="tab" :aria-selected="grantTab === 'permission'" :class="{ active: grantTab === 'permission' }" @click="grantTab = 'permission'">
              权限点（{{ selectedPermissionIds.length }}/{{ permissions.length }}）
            </button>
          </div>
          <div class="grant-layout">
            <section v-if="grantTab === 'menu'" class="grant-section">
              <div class="card menu-tree">
                <div class="menu-tree-toolbar">
                  <div class="grant-toolbar-head">
                    <span class="toolbar-summary">菜单树</span>
                    <span class="grant-tree-hint">勾选父级会同时勾选其子菜单</span>
                  </div>
                  <div class="grant-toolbar-actions">
                    <button class="text-button" @click="selectedMenuIds = flatMenus.map((menu) => menu.id)">全选</button>
                    <button class="text-button" @click="selectedMenuIds = []">清空</button>
                  </div>
                </div>
                <GrantMenuTreeNode
                  v-for="menu in menus"
                  :key="menu.id"
                  :node="menu"
                  :selected="selectedMenuIds"
                  @toggle="toggleMenu"
                />
                <div v-if="!menus.length" class="empty-state">暂无菜单，请先在菜单管理中新增</div>
              </div>
            </section>
            <section v-else class="grant-section">
              <div v-for="group in permissionGroups" :key="group.module" class="grant-group">
                <div class="grant-group-head">
                  <strong>{{ group.module }}</strong>
                  <button class="text-button" @click="togglePermissionGroup(group.module, true)">全选</button>
                  <button class="text-button" @click="togglePermissionGroup(group.module, false)">清空</button>
                </div>
                <div class="grant-group-body">
                  <label v-for="permission in group.items" :key="permission.id" class="checkbox-row">
                    <input v-model="selectedPermissionIds" type="checkbox" :value="permission.id" />
                    <span><code>{{ permission.code }}</code> · {{ permission.name }}</span>
                  </label>
                </div>
              </div>
            </section>
          </div>
        </div>
        <div class="drawer-actions">
          <button class="secondary-button" @click="showGrantModal = false">取消</button>
          <button class="primary-button" :disabled="saving" @click="saveGrant">{{ saving ? '保存中...' : '保存授权' }}</button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.danger-text { color: var(--danger); }
.locked-action { cursor: help; opacity: .65; border-style: dashed; }
.locked-action:hover:not(:disabled) { border-color: var(--line-strong); background: transparent; color: var(--muted); }
.grant-tabs { display: flex; width: 100%; margin-bottom: 1rem; }
.grant-tabs button { flex: 1; }
.grant-toolbar-head { display: flex; align-items: baseline; gap: .59rem; min-width: 0; }
.grant-tree-hint { color: var(--muted); font-size: .9rem; }
.grant-toolbar-actions { display: flex; align-items: center; gap: .24rem; }
</style>
