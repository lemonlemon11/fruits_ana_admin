<script setup lang="ts">
import { computed, ref } from 'vue'
import type { MenuNode } from '../types'

const props = defineProps<{ node: MenuNode; selected: number[] }>()
const emit = defineEmits<{
  toggle: [node: MenuNode]
}>()

const expanded = ref(true)
const children = computed(() => props.node.children || [])
const hasChildren = computed(() => children.value.length > 0)
// 只有整棵子树都被选中才算勾选，否则部分选中显示为半选，避免父级状态说谎
const subtreeIds = computed(() => [props.node.id, ...collectIds(props.node)])
const checked = computed(() => subtreeIds.value.every((id) => props.selected.includes(id)))
const partial = computed(
  () => !checked.value && subtreeIds.value.some((id) => props.selected.includes(id)),
)

const typeLabel: Record<MenuNode['menu_type'], string> = {
  directory: '目录',
  menu: '菜单',
  button: '按钮',
}

function collectIds(node: MenuNode): number[] {
  const ids: number[] = []
  for (const child of node.children || []) ids.push(child.id, ...collectIds(child))
  return ids
}
</script>

<template>
  <div class="menu-tree-node">
    <div class="menu-tree-row grant-tree-row">
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

      <label class="grant-tree-main">
        <input
          type="checkbox"
          :checked="checked"
          :indeterminate.prop="partial"
          :aria-label="`选择菜单 ${props.node.name}`"
          @change="emit('toggle', props.node)"
        />
        <span class="tag menu-type-tag" :class="props.node.menu_type">{{ typeLabel[props.node.menu_type] }}</span>
        <strong>{{ props.node.name }}</strong>
        <span class="menu-tree-meta">{{ props.node.route_path || props.node.permission_code || '无路由' }}</span>
        <span class="tag" :class="props.node.is_active ? 'success' : 'danger'">{{ props.node.is_active ? '启用' : '停用' }}</span>
      </label>
    </div>

    <div v-if="expanded && hasChildren" class="menu-tree-children">
      <GrantMenuTreeNode
        v-for="child in children"
        :key="child.id"
        :node="child"
        :selected="selected"
        @toggle="emit('toggle', $event)"
      />
    </div>
  </div>
</template>

<style scoped>
/* 复用菜单管理的树行样式，只把右侧操作区换成勾选框。 */
.menu-tree-row.grant-tree-row { grid-template-columns: 1.65rem minmax(0, 1fr); }
.grant-tree-main {
  display: grid;
  grid-template-columns: auto auto minmax(120px, 1fr) minmax(110px, 1.2fr) auto;
  align-items: center;
  gap: .65rem;
  min-width: 0;
  cursor: pointer;
}
.grant-tree-main input { width: 1.18rem; height: 1.18rem; accent-color: var(--primary); }
.grant-tree-main > strong { min-width: 0; overflow-wrap: anywhere; }
@media (max-width: 760px) {
  .grant-tree-main { grid-template-columns: auto auto minmax(0, 1fr) auto; }
  .grant-tree-main .menu-tree-meta { display: none; }
}
</style>
