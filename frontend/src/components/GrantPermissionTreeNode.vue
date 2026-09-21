<script setup lang="ts">
import { computed, ref } from 'vue'

export interface GrantPermissionNode {
  key: string
  name: string
  /** 只有 permission 才是叶子节点带勾选框，menu/directory 只做分组容器 */
  nodeType: 'directory' | 'menu' | 'permission'
  /** 权限码描述，仅 permission 节点展示 */
  codeDescription?: string
  /** 叶子节点的权限 ID */
  permissionIds: number[]
  children: GrantPermissionNode[]
}

const props = defineProps<{
  node: GrantPermissionNode
  selected: number[]
}>()
const emit = defineEmits<{
  toggle: [permissionIds: number[]]
}>()

const expanded = ref(true)
const children = computed(() => props.node.children || [])
const hasChildren = computed(() => children.value.length > 0)

function collectAllIds(n: GrantPermissionNode): number[] {
  return [...n.permissionIds, ...n.children.flatMap(collectAllIds)]
}

const subtreeIds = computed(() => collectAllIds(props.node))
const checked = computed(
  () => subtreeIds.value.length > 0 && subtreeIds.value.every((id) => props.selected.includes(id)),
)
const partial = computed(
  () => !checked.value && subtreeIds.value.some((id) => props.selected.includes(id)),
)

function handleToggle(): void {
  if (subtreeIds.value.length === 0) return
  emit('toggle', subtreeIds.value)
}
</script>

<template>
  <div class="perm-tree-node">
    <div class="perm-tree-row">
      <button
        v-if="hasChildren"
        class="perm-tree-toggle"
        type="button"
        :aria-expanded="expanded"
        :aria-label="expanded ? '收起' : '展开'"
        @click="expanded = !expanded"
      >
        <span>{{ expanded ? '▾' : '▸' }}</span>
      </button>
      <span v-else class="perm-tree-toggle-placeholder"></span>

      <!-- 目录/菜单节点：纯容器，不带勾选框 -->
      <span v-if="node.nodeType === 'directory' || node.nodeType === 'menu'" class="perm-tree-group-label" :class="{ 'perm-tree-dir': node.nodeType === 'directory' }">
        <span class="tag menu-type-tag" :class="node.nodeType">{{ node.nodeType === 'directory' ? '目录' : '菜单' }}</span>
        <strong>{{ node.name }}</strong>
        <span v-if="hasChildren" class="perm-count">{{ subtreeIds.length }} 个权限</span>
      </span>

      <!-- 权限点叶子节点：带勾选框 -->
      <label v-else class="perm-tree-leaf">
        <input
          type="checkbox"
          :checked="checked"
          :indeterminate.prop="partial"
          :aria-label="`选择权限 ${node.name}`"
          @change="handleToggle"
        />
        <span>{{ node.name }}</span>
        <code class="perm-code">{{ node.codeDescription }}</code>
      </label>
    </div>
    <div v-if="expanded && hasChildren" class="perm-tree-children">
      <GrantPermissionTreeNode
        v-for="child in children"
        :key="child.key"
        :node="child"
        :selected="selected"
        @toggle="emit('toggle', $event)"
      />
    </div>
  </div>
</template>

<style scoped>
.perm-tree-node { user-select: none; }
.perm-tree-row {
  display: grid;
  grid-template-columns: 1.65rem minmax(0, 1fr);
  align-items: center;
  padding: .2rem 0;
}
.perm-tree-toggle,
.perm-tree-toggle-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.65rem;
  height: 1.65rem;
}
.perm-tree-toggle {
  border: none;
  background: none;
  cursor: pointer;
  color: var(--muted);
  font-size: .8rem;
  padding: 0;
}
.perm-tree-toggle:hover { color: var(--text); }
.perm-tree-toggle-placeholder { content: ''; }
.perm-tree-group-label {
  display: inline-flex;
  align-items: center;
  gap: .5rem;
  min-width: 0;
}
.perm-tree-dir > strong { font-weight: 700; }
.perm-tree-group-label > strong { font-weight: 600; }
.perm-count { color: var(--muted); font-size: .85rem; }
.perm-tree-leaf {
  display: inline-flex;
  align-items: center;
  gap: .5rem;
  cursor: pointer;
  min-width: 0;
}
.perm-tree-leaf input {
  width: 1.18rem;
  height: 1.18rem;
  accent-color: var(--primary);
  flex-shrink: 0;
}
.perm-code {
  color: var(--muted);
  font-size: .82rem;
  background: var(--bg);
  padding: .05rem .4rem;
  border-radius: 3px;
}
.perm-tree-children { padding-left: 1.25rem; }
</style>
