<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import MenuTreeNode from '../components/MenuTreeNode.vue'
import { del, get, patch, post } from '../api/client'
import { confirmAction, notify } from '../feedback'
import { hasPermission } from '../auth'
import type { MenuNode } from '../types'

type FlatMenu = MenuNode & { depth: number }

const tree = ref<MenuNode[]>([])
const flat = computed<FlatMenu[]>(() => {
  const result: FlatMenu[] = []
  const walk = (nodes: MenuNode[], depth = 0) => {
    for (const node of nodes) {
      result.push({ ...node, depth })
      if (node.children.length) walk(node.children, depth + 1)
    }
  }
  walk(tree.value)
  return result
})
const error = ref('')
const saving = ref(false)
const showModal = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({
  parent_id: null as number | null,
  name: '',
  menu_type: 'menu' as 'directory' | 'menu' | 'button',
  route_path: '',
  component: '',
  icon: '',
  permission_code: '',
  sort_order: 0,
  is_active: true,
})

async function load() {
  error.value = ''
  try {
    const data = await get<{ items: MenuNode[] }>('/api/admin/menus/tree')
    tree.value = data.items
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败'
  }
}

function openCreate() {
  editingId.value = null
  Object.assign(form, {
    parent_id: null,
    name: '',
    menu_type: 'menu',
    route_path: '',
    component: '',
    icon: '',
    permission_code: '',
    sort_order: 0,
    is_active: true,
  })
  showModal.value = true
}

function openEdit(menu: FlatMenu) {
  editingId.value = menu.id
  Object.assign(form, {
    parent_id: menu.parent_id,
    name: menu.name,
    menu_type: menu.menu_type,
    route_path: menu.route_path || '',
    component: menu.component || '',
    icon: menu.icon || '',
    permission_code: menu.permission_code || '',
    sort_order: menu.sort_order,
    is_active: menu.is_active,
  })
  showModal.value = true
}

async function save() {
  saving.value = true
  try {
    const payload = {
      parent_id: form.parent_id,
      name: form.name,
      menu_type: form.menu_type,
      route_path: form.route_path || null,
      component: form.component || null,
      icon: form.icon || null,
      permission_code: form.permission_code || null,
      sort_order: form.sort_order,
      is_active: form.is_active,
    }
    if (editingId.value === null) {
      await post('/api/admin/menus', payload)
      notify('菜单已创建')
    } else {
      await patch(`/api/admin/menus/${editingId.value}`, payload)
      notify('菜单已更新')
    }
    showModal.value = false
    await load()
  } catch (err) {
    notify(err instanceof Error ? err.message : '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

async function removeMenu(menu: FlatMenu) {
  const ok = await confirmAction(`确认删除菜单 ${menu.name}？其子节点也会一并删除。`, {
    title: '删除菜单',
    confirmText: '删除',
  })
  if (!ok) return
  try {
    await del(`/api/admin/menus/${menu.id}`)
    notify('菜单已删除')
    await load()
  } catch (err) {
    notify(err instanceof Error ? err.message : '删除失败', 'error')
  }
}

onMounted(load)
</script>

<template>
  <section class="page-stack">
    <p v-if="error" class="error">{{ error }}</p>

    <div class="card menu-tree">
      <div class="menu-tree-toolbar">
        <span class="toolbar-summary">菜单树</span>
        <button v-if="hasPermission('admin:menu:create')" class="primary-button" @click="openCreate">新增菜单</button>
      </div>
      <MenuTreeNode
        v-for="menu in tree"
        :key="menu.id"
        :node="menu"
        @edit="openEdit"
        @remove="removeMenu"
      />
      <div v-if="!tree.length" class="empty-state">暂无菜单，请先新增目录或菜单</div>
    </div>

    <div v-if="showModal" class="drawer-mask" @click.self="showModal = false">
      <div class="drawer" role="dialog" aria-modal="true" aria-label="菜单编辑">
        <div class="drawer-header">
          <div class="drawer-title">{{ editingId === null ? '新增菜单' : '编辑菜单' }}</div>
          <button class="link-button" @click="showModal = false">关闭</button>
        </div>
        <div class="drawer-body">
        <div class="field">
          <label>父级菜单</label>
          <select v-model="form.parent_id" class="select">
            <option :value="null">无</option>
            <option v-for="menu in flat.filter((item) => item.id !== editingId)" :key="menu.id" :value="menu.id">
              {{ '　'.repeat(menu.depth) }}{{ menu.name }}
            </option>
          </select>
        </div>
        <div class="field">
          <label>名称</label>
          <input v-model="form.name" class="input" />
        </div>
        <div class="field">
          <label>类型</label>
          <select v-model="form.menu_type" class="select">
            <option value="directory">目录</option>
            <option value="menu">菜单</option>
            <option value="button">按钮</option>
          </select>
        </div>
        <div class="field">
          <label>路由路径</label>
          <input v-model="form.route_path" class="input" placeholder="/admin/users" />
        </div>
        <div class="field">
          <label>组件名</label>
          <input v-model="form.component" class="input" placeholder="UsersView" />
        </div>
        <div class="field">
          <label>图标名</label>
          <input v-model="form.icon" class="input" placeholder="Users" />
        </div>
        <div class="field">
          <label>权限标识</label>
          <input v-model="form.permission_code" class="input" placeholder="overview:view" />
        </div>
        <div class="field">
          <label>排序</label>
          <input v-model.number="form.sort_order" class="input" type="number" />
        </div>
        <div class="field checkbox-row">
          <input id="menu-active" v-model="form.is_active" type="checkbox" />
          <label for="menu-active">启用菜单</label>
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
