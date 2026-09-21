<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { del, get, patch, post, put } from '../api/client'
import { confirmAction, notify } from '../feedback'
import { hasPermission } from '../auth'
import DataTable, { type DataTableColumn } from '../components/DataTable.vue'
import GrantMenuTreeNode from '../components/GrantMenuTreeNode.vue'
import GrantPermissionTreeNode, { type GrantPermissionNode } from '../components/GrantPermissionTreeNode.vue'
import { useEscapeClose } from '../composables/useEscapeClose'
import Pencil from '@lucide/vue/dist/esm/icons/pencil.mjs'
import ShieldCheck from '@lucide/vue/dist/esm/icons/shield-check.mjs'
import Trash2 from '@lucide/vue/dist/esm/icons/trash.mjs'
import type { ListResponse, MenuNode, PermissionItem, RoleItem, UserItem } from '../types'

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
const showUsersModal = ref(false)
const usersRole = ref<RoleItem | null>(null)
const roleUsers = ref<UserItem[]>([])
const loadingRoleUsers = ref(false)
const usersError = ref('')
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
useEscapeClose(() => !showGrantModal.value && !showModal.value && showUsersModal.value, () => {
  showUsersModal.value = false
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
      get<ListResponse<PermissionItem>>('/api/admin/permissions?scope=business'),
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

async function openRoleUsers(role: RoleItem) {
  usersRole.value = role
  roleUsers.value = []
  usersError.value = ''
  loadingRoleUsers.value = true
  showUsersModal.value = true
  try {
    const data = await get<ListResponse<UserItem>>(`/api/admin/roles/${role.id}/users`)
    roleUsers.value = data.items
  } catch (err) {
    usersError.value = err instanceof Error ? err.message : '用户列表加载失败'
  } finally {
    loadingRoleUsers.value = false
  }
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
    selectedPermissionIds.value = (role.permission_ids || []).filter((id) =>
      permissions.value.some((permission) => permission.id === id),
    )
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
    notify(err instanceof Error ? err.message : '保存授权失败', 'error')
  } finally {
    saving.value = false
  }
}

async function removeRole(role: RoleItem) {
  if (!await confirmAction(`确定要删除角色「${role.name}」吗？`)) return
  try {
    await del(`/api/admin/roles/${role.id}`)
    notify('角色已删除')
    await load()
  } catch (err) {
    notify(err instanceof Error ? err.message : '删除失败', 'error')
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

function togglePermissionIds(permissionIds: number[]) {
  if (permissionIds.length === 0) return
  const allSelected = permissionIds.every((id) => selectedPermissionIds.value.includes(id))
  selectedPermissionIds.value = allSelected
    ? selectedPermissionIds.value.filter((id) => !permissionIds.includes(id))
    : Array.from(new Set([...selectedPermissionIds.value, ...permissionIds]))
}

/**
 * 基于菜单树构建权限树。
 *
 * 遍历菜单树，为每个菜单节点附加其 permission_code 对应的权限点，
 * 以及该节点下无关联菜单的游离权限（module 匹配菜单 key）。
 * 最终产出树状 GrantPermissionNode[]，让权限点展示在所属菜单下。
 */
/**
 * 基于菜单树构建权限树。
 *
 * 菜单/目录节点只做分组容器，不带勾选框；
 * 权限点全作为叶子节点挂在所属菜单下。
 * 未关联菜单的游离权限按 module 分组独立展示。
 */

const permissionTree = computed(() => {
  const permMap = new Map<string, PermissionItem>()
  for (const p of permissions.value) {
    permMap.set(p.code, p)
  }

  // 从 permission_code 提取模块前缀（"settlement:list" -> "settlement"）
  function codePrefix(code: string): string {
    const idx = code.indexOf(':')
    return idx > 0 ? code.substring(0, idx) : code
  }

  // 构建 module → 主菜单的映射（取第一个匹配的菜单）
  // 用于 action 权限（import:upload、entry:create 等）归到对应菜单下
  const moduleMenuMap = new Map<string, MenuNode>()
  function walkModule(nodes: MenuNode[]) {
    for (const menu of nodes) {
      if (menu.permission_code) {
        const prefix = codePrefix(menu.permission_code)
        if (!moduleMenuMap.has(prefix)) moduleMenuMap.set(prefix, menu)
      }
      if (menu.children?.length) walkModule(menu.children)
    }
  }
  walkModule(menus.value)

  // 记录已分配的权限 ID
  const assigned = new Set<number>()

  function buildTree(menuNodes: MenuNode[]): GrantPermissionNode[] {
    const result: GrantPermissionNode[] = []
    for (const menu of menuNodes) {
      const permChildren: GrantPermissionNode[] = []

      // 1) permission_code 精确匹配（菜单的主权限点）
      if (menu.permission_code) {
        const perm = permMap.get(menu.permission_code)
        if (perm) {
          assigned.add(perm.id)
          permChildren.push({
            key: `perm:${perm.id}`,
            name: perm.name,
            codeDescription: perm.code,
            nodeType: 'permission',
            permissionIds: [perm.id],
            children: [],
          })
        }
      }

      // 2) 同模块的 action 权限（按 module 字段匹配）
      const prefix = menu.permission_code ? codePrefix(menu.permission_code) : ''
      if (prefix) {
        for (const p of permissions.value) {
          if (!assigned.has(p.id) && p.module === prefix) {
            assigned.add(p.id)
            permChildren.push({
              key: `perm:${p.id}`,
              name: p.name,
              codeDescription: p.code,
              nodeType: 'permission',
              permissionIds: [p.id],
              children: [],
            })
          }
        }
      }

      // 递归子菜单
      const subMenus = buildTree(menu.children || [])

      // 没有内容的节点不展示
      if (permChildren.length === 0 && subMenus.length === 0) continue

      result.push({
        key: `menu:${menu.id}`,
        name: menu.name,
        nodeType: menu.menu_type === 'directory' ? 'directory' : 'menu',
        permissionIds: [],
        children: [...subMenus, ...permChildren],
      })
    }
    return result
  }

  const tree = buildTree(menus.value)

  // 未匹配到任何菜单的权限（如 module 不在菜单中的）
  const unassigned = permissions.value.filter((p) => !assigned.has(p.id))
  if (unassigned.length > 0) {
    tree.push({
      key: 'other',
      name: '其他权限',
      nodeType: 'directory',
      permissionIds: [],
      children: unassigned.map((p) => ({
        key: `perm:${p.id}`,
        name: p.name,
        codeDescription: p.code,
        nodeType: 'permission',
        permissionIds: [p.id],
        children: [],
      })),
    })
  }

  return tree
})


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
      <template #cell-user_count="{ row }">
        <button class="table-action" type="button" :disabled="row.user_count === 0" @click="openRoleUsers(row)">
          {{ row.user_count }}
        </button>
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
              <div class="card menu-tree">
                <div class="menu-tree-toolbar">
                  <div class="grant-toolbar-head">
                    <span class="toolbar-summary">权限树</span>
                    <span class="grant-tree-hint">按菜单结构展示，勾选父级会同时勾选其下所有权限</span>
                  </div>
                  <div class="grant-toolbar-actions">
                    <button class="text-button" @click="selectedPermissionIds = permissions.map((p) => p.id)">全选</button>
                    <button class="text-button" @click="selectedPermissionIds = []">清空</button>
                  </div>
                </div>
                <GrantPermissionTreeNode
                  v-for="node in permissionTree"
                  :key="node.key"
                  :node="node"
                  :selected="selectedPermissionIds"
                  @toggle="togglePermissionIds"
                />
                <div v-if="!permissionTree.length" class="empty-state">暂无权限点</div>
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

    <div v-if="showUsersModal && usersRole" class="drawer-mask" @click.self="showUsersModal = false">
      <div class="drawer" role="dialog" aria-modal="true" aria-label="查看角色用户">
        <div class="drawer-header">
          <div class="drawer-title">角色用户：{{ usersRole.name }}</div>
          <button class="link-button" @click="showUsersModal = false">关闭</button>
        </div>
        <div class="drawer-body">
          <p v-if="usersError" class="error">{{ usersError }}</p>
          <div v-if="loadingRoleUsers" class="empty-state">正在加载…</div>
          <div v-else-if="roleUsers.length" class="role-user-list">
            <div v-for="user in roleUsers" :key="user.id" class="role-user-row">
              <span class="role-user-name">{{ user.display_name }}</span>
              <span class="tag" :class="user.is_active ? 'success' : 'danger'">
                {{ user.is_active ? '启用' : '禁用' }}
              </span>
            </div>
          </div>
          <div v-else class="empty-state">该角色下暂无用户</div>
        </div>
        <div class="drawer-actions">
          <button class="secondary-button" @click="showUsersModal = false">关闭</button>
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
.role-user-list { display: flex; flex-direction: column; gap: .5rem; }
.role-user-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: .75rem;
  padding: .68rem .75rem;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: var(--surface);
}
.role-user-name { font-weight: 700; min-width: 0; overflow-wrap: anywhere; }
</style>
