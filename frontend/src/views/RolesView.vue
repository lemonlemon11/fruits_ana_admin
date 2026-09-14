<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { del, get, patch, post, put } from '../api/client'
import { confirmAction, notify } from '../feedback'
import { hasPermission } from '../auth'
import type { ListResponse, MenuItem, PermissionItem, RoleItem } from '../types'

const roles = ref<RoleItem[]>([])
const menus = ref<MenuItem[]>([])
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
  const [menuData, permissionData] = await Promise.all([
    get<{ items: MenuItem[] }>('/api/admin/menus'),
    get<ListResponse<PermissionItem>>('/api/admin/permissions'),
  ])
  menus.value = menuData.items
  permissions.value = permissionData.items
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

async function openGrant(role: RoleItem) {
  grantRole.value = role
  selectedMenuIds.value = [...role.menu_ids]
  selectedPermissionIds.value = [...role.permission_ids]
  showGrantModal.value = true
}

async function saveGrant() {
  if (!grantRole.value) return
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
  const walk = (nodes: MenuItem[], depth = 0) => {
    for (const node of nodes) {
      result.push({ id: node.id, name: node.name, depth })
      if (node.children.length) walk(node.children, depth + 1)
    }
  }
  walk(menus.value)
  return result
})

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
    <div class="page-header">
      <div class="page-actions">
        <button v-if="hasPermission('admin:role:create')" class="primary-button" @click="openCreate">新增角色</button>
      </div>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <div class="table-wrap">
    <table class="table">
      <thead>
        <tr>
          <th>ID</th>
          <th>角色名称</th>
          <th>编码</th>
          <th>状态</th>
          <th>用户数</th>
          <th>菜单数</th>
          <th>权限数</th>
          <th>说明</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="role in roles" :key="role.id">
          <td>{{ role.id }}</td>
          <td>{{ role.name }} <span v-if="role.is_system" class="tag">系统</span></td>
          <td>{{ role.code }}</td>
          <td><span class="tag" :class="role.is_active ? 'success' : 'danger'">{{ role.is_active ? '启用' : '停用' }}</span></td>
          <td>{{ role.user_count }}</td>
          <td>{{ role.menu_ids.length }}</td>
          <td>{{ role.permission_ids.length }}</td>
          <td>{{ role.description || '—' }}</td>
          <td>
            <button v-if="hasPermission('admin:role:update')" class="link-button" :disabled="busyRoleId === role.id" @click="openEdit(role)">编辑</button>
            <button v-if="hasPermission('admin:role:grant')" class="link-button" :disabled="role.code === 'super_admin' || role.code === 'fruit_admin' || busyRoleId === role.id" @click="openGrant(role)">授权</button>
            <button v-if="hasPermission('admin:role:delete') && !role.is_system" class="link-button danger-text" :disabled="busyRoleId === role.id" @click="removeRole(role)">删除</button>
          </td>
        </tr>
      </tbody>
    </table>
    </div>
    <div class="empty-state" v-if="!roles.length">暂无角色</div>

    <div v-if="showModal" class="modal-mask">
      <div class="modal">
        <div class="modal-header">
          <div class="modal-title">{{ editingId === null ? '新增角色' : '编辑角色' }}</div>
          <button class="link-button" @click="showModal = false">关闭</button>
        </div>
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
        <div class="modal-actions">
          <button class="secondary-button" @click="showModal = false">取消</button>
          <button class="primary-button" :disabled="saving" @click="save">{{ saving ? '保存中...' : '保存' }}</button>
        </div>
      </div>
    </div>

    <div v-if="showGrantModal && grantRole" class="modal-mask">
      <div class="modal">
        <div class="modal-header">
          <div class="modal-title">分配角色权限：{{ grantRole.name }}</div>
          <button class="link-button" @click="showGrantModal = false">关闭</button>
        </div>
        <div class="grant-layout">
          <section class="grant-section">
            <h3>菜单</h3>
            <label v-for="menu in flatMenus" :key="menu.id" class="checkbox-row grant-menu-row" :style="{ paddingLeft: `${menu.depth * 18}px` }">
              <input v-model="selectedMenuIds" type="checkbox" :value="menu.id" />
              {{ menu.name }}
            </label>
          </section>
          <section class="grant-section">
            <h3>权限点</h3>
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
        <div class="modal-actions">
          <button class="secondary-button" @click="showGrantModal = false">取消</button>
          <button class="primary-button" :disabled="saving" @click="saveGrant">{{ saving ? '保存中...' : '保存授权' }}</button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.danger-text { color: var(--danger); }
</style>
