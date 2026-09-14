<script setup lang="ts">
import { computed, ref } from 'vue'
import { hasPermission } from '../auth'
import type { MenuNode } from '../types'

const props = defineProps<{ node: MenuNode }>()
const emit = defineEmits<{
  edit: [node: MenuNode]
  remove: [node: MenuNode]
}>()

const expanded = ref(true)
const hasChildren = computed(() => props.node.children.length > 0)

const typeLabel: Record<MenuNode['menu_type'], string> = {
  directory: '目录',
  menu: '菜单',
  button: '按钮',
}
</script>

<template>
  <div class="menu-tree-node">
    <div class="menu-tree-row">
      <button
        v-if="hasChildren"
        class="menu-tree-toggle"
        type="button"
        :aria-expanded="expanded"
        :aria-label="expanded ? '收起子菜单' : '展开子菜单'"
        @click="expanded = !expanded"
      >
        <span>{{ expanded ? '▾' : '▸' }}</span>
      </button>
      <span v-else class="menu-tree-toggle-placeholder"></span>

      <span class="tag menu-type-tag" :class="props.node.menu_type">{{ typeLabel[props.node.menu_type] }}</span>
      <strong>{{ props.node.name }}</strong>
      <span class="menu-tree-meta">
        <template v-if="props.node.route_path">{{ props.node.route_path }}</template>
        <template v-else>{{ props.node.permission_code || '无路由' }}</template>
      </span>
      <span class="tag" :class="props.node.is_active ? 'success' : 'danger'">{{ props.node.is_active ? '启用' : '停用' }}</span>
      <div class="menu-tree-actions">
        <button v-if="hasPermission('admin:menu:update')" class="link-button" @click="emit('edit', props.node)">编辑</button>
        <button v-if="hasPermission('admin:menu:delete')" class="link-button danger-text" @click="emit('remove', props.node)">删除</button>
      </div>
    </div>

    <div v-if="expanded && hasChildren" class="menu-tree-children">
      <MenuTreeNode
        v-for="child in props.node.children"
        :key="child.id"
        :node="child"
        @edit="emit('edit', $event)"
        @remove="emit('remove', $event)"
      />
    </div>
  </div>
</template>
