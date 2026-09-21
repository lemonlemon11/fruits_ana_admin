<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import GripVertical from '@lucide/vue/dist/esm/icons/grip-vertical.mjs'
import Plus from '@lucide/vue/dist/esm/icons/plus.mjs'
import Trash2 from '@lucide/vue/dist/esm/icons/trash.mjs'
import { del, get, patch, post, put } from '../api/client'
import { confirmAction, notify } from '../feedback'
import { useEscapeClose } from '../composables/useEscapeClose'
import type { EntryFieldOption, EntryFieldOptionList } from '../types'

type FieldKey = 'market' | 'variety'

interface FieldNode {
  key: FieldKey
  label: string
  hint: string
  validate: (value: string) => string | null
}

const FIELD_TREE: Array<{ title: string; children: FieldNode[] }> = [
  {
    title: '基本信息',
    children: [
      { key: 'market', label: '市场', hint: '市场名称，支持后续随时新增。', validate: () => null },
    ],
  },
  {
    title: '销售明细',
    children: [
      {
        key: 'variety',
        label: '品种',
        hint: '品种允许 A-F，以及组合等级 AB、BC。',
        validate: (value) => /^(?:[A-F]|AB|BC)$/.test(value) ? null : '品种必须是 A-F 或 AB、BC',
      },
    ],
  },
]

const flatFields = FIELD_TREE.flatMap((group) => group.children)
const activeKey = ref<FieldKey>(flatFields[0]?.key ?? 'market')
const activeField = computed(() => flatFields.find((item) => item.key === activeKey.value) ?? flatFields[0])

const items = ref<EntryFieldOption[]>([])
const fieldCounts = reactive<Record<FieldKey, number>>({ market: 0, variety: 0 })
const error = ref('')
const saving = ref(false)
const reordering = ref(false)
const draggingId = ref<number | null>(null)
const showModal = ref(false)
const form = reactive({
  value: '',
  is_active: true,
})
// 行内编辑草稿：仅在输入未提交时覆盖服务端值，提交失败即回退。
const drafts = ref<Record<number, string>>({})
const savingIds = ref<number[]>([])

function isSaving(item: EntryFieldOption) {
  return savingIds.value.includes(item.id)
}

function startSaving(item: EntryFieldOption) {
  if (!savingIds.value.includes(item.id)) savingIds.value = [...savingIds.value, item.id]
}

function endSaving(item: EntryFieldOption) {
  savingIds.value = savingIds.value.filter((id) => id !== item.id)
}

function draftOf(item: EntryFieldOption) {
  return drafts.value[item.id] ?? item.value
}

function onDraftInput(item: EntryFieldOption, event: Event) {
  drafts.value[item.id] = (event.target as HTMLInputElement).value
}

useEscapeClose(() => showModal.value, () => {
  showModal.value = false
})

async function load() {
  error.value = ''
  try {
    const data = await get<EntryFieldOptionList>(`/api/admin/entry-field-options?field=${activeKey.value}`)
    items.value = data.items
    fieldCounts[activeKey.value] = data.total
    drafts.value = {}
    savingIds.value = []
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '加载失败'
  }
}

function selectField(key: FieldKey) {
  if (activeKey.value === key) return
  activeKey.value = key
  void load()
}

function openCreate() {
  form.value = ''
  form.is_active = true
  showModal.value = true
}

// 列表内改完即存：失焦或回车提交，失败或校验不过即回退为原值。
async function commitValue(item: EntryFieldOption) {
  if (isSaving(item)) return
  const value = draftOf(item).trim()
  if (value === item.value) {
    drafts.value[item.id] = item.value
    return
  }
  if (!value) {
    drafts.value[item.id] = item.value
    notify('请输入选项值', 'error')
    return
  }
  const invalid = activeField.value.validate(value)
  if (invalid) {
    drafts.value[item.id] = item.value
    notify(invalid, 'error')
    return
  }
  startSaving(item)
  try {
    await patch(`/api/admin/entry-field-options/${item.id}`, { value })
    item.value = value
    drafts.value[item.id] = value
    notify('字段选项已更新')
  } catch (caught) {
    drafts.value[item.id] = item.value
    notify(caught instanceof Error ? caught.message : '保存失败', 'error')
  } finally {
    endSaving(item)
  }
}

// 启用状态勾选即存；失败时把勾选状态改回去，让 DOM 一并回退。
async function toggleActive(item: EntryFieldOption, event: Event) {
  if (isSaving(item)) return
  const next = (event.target as HTMLInputElement).checked
  startSaving(item)
  try {
    await patch(`/api/admin/entry-field-options/${item.id}`, { is_active: next })
    item.is_active = next
    notify(next ? '字段选项已启用' : '字段选项已停用')
  } catch (caught) {
    item.is_active = !next
    notify(caught instanceof Error ? caught.message : '保存失败', 'error')
  } finally {
    endSaving(item)
  }
}

function blurInput(event: Event) {
  ;(event.target as HTMLElement).blur()
}

async function save() {
  const value = form.value.trim()
  if (!value) {
    notify('请输入选项值', 'error')
    return
  }
  const invalid = activeField.value.validate(value)
  if (invalid) {
    notify(invalid, 'error')
    return
  }
  saving.value = true
  try {
    await post('/api/admin/entry-field-options', {
      field_key: activeKey.value,
      value,
      sort_order: items.value.length,
      is_active: form.is_active,
    })
    notify('字段选项已创建')
    showModal.value = false
    await load()
  } catch (caught) {
    notify(caught instanceof Error ? caught.message : '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

async function removeOption(item: EntryFieldOption) {
  const ok = await confirmAction(`确认删除${activeField.value.label}选项 ${item.value}？`, {
    title: '删除字段选项',
    confirmText: '删除',
  })
  if (!ok) return
  try {
    await del(`/api/admin/entry-field-options/${item.id}`)
    notify('字段选项已删除')
    await load()
  } catch (caught) {
    notify(caught instanceof Error ? caught.message : '删除失败', 'error')
  }
}

function startDrag(item: EntryFieldOption, event: DragEvent) {
  draggingId.value = item.id
  event.dataTransfer?.setData('text/plain', String(item.id))
  if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move'
}

function onDrop(targetId: number) {
  if (draggingId.value === null || draggingId.value === targetId) return
  const from = items.value.findIndex((item) => item.id === draggingId.value)
  const to = items.value.findIndex((item) => item.id === targetId)
  if (from < 0 || to < 0) return
  const [moved] = items.value.splice(from, 1)
  items.value.splice(to, 0, moved)
  void saveOrder()
}

async function saveOrder() {
  reordering.value = true
  try {
    const data = await put<EntryFieldOptionList>('/api/admin/entry-field-options/reorder', {
      field_key: activeKey.value,
      item_ids: items.value.map((item) => item.id),
    })
    items.value = data.items
    notify('排序已保存')
  } catch (caught) {
    notify(caught instanceof Error ? caught.message : '排序保存失败', 'error')
    await load()
  } finally {
    draggingId.value = null
    reordering.value = false
  }
}

onMounted(async () => {
  await Promise.all(flatFields.map(async (field) => {
    try {
      const data = await get<EntryFieldOptionList>(`/api/admin/entry-field-options?field=${field.key}`)
      fieldCounts[field.key] = data.total
    } catch {
      // 单字段计数失败不阻塞页面加载，主面板会单独展示错误。
    }
  }))
  await load()
})
</script>

<template>
  <section class="page-stack">
    <div class="field-config-shell">
      <aside class="field-tree list-card">
        <div class="field-tree-head">
          <strong>录单字段</strong>
          <span>点击左侧字段，配置右侧选项；列表内直接修改，改完自动保存</span>
        </div>
        <div v-for="group in FIELD_TREE" :key="group.title" class="field-tree-group">
          <div class="field-tree-group-title">{{ group.title }}</div>
          <button
            v-for="field in group.children"
            :key="field.key"
            type="button"
            class="field-tree-node"
            :class="{ active: activeKey === field.key }"
            @click="selectField(field.key)"
          >
            <span>{{ field.label }}</span>
            <small>{{ fieldCounts[field.key] }} 项</small>
          </button>
        </div>
      </aside>

      <main class="field-config-main list-card">
        <div class="toolbar">
          <div>
            <h2>{{ activeField.label }}选项</h2>
            <p class="field-hint">{{ activeField.hint }}</p>
            <p class="field-hint">可直接在列表里改选项值和启用状态，离开输入框或回车即保存。</p>
          </div>
          <button class="primary-button toolbar-action" type="button" @click="openCreate">
            <Plus :size="16" :stroke-width="2" aria-hidden="true" />新增{{ activeField.label }}选项
          </button>
        </div>

        <p v-if="error" class="error">{{ error }}</p>

        <div v-if="items.length" class="field-option-list" :class="{ 'is-dragging': draggingId !== null }">
          <div
            v-for="(item, index) in items"
            :key="item.id"
            class="field-option-row"
            :class="{ dragging: draggingId === item.id, saving: isSaving(item) }"
            :aria-busy="isSaving(item)"
            @dragover.prevent
            @drop="onDrop(item.id)"
          >
            <button
              class="drag-handle"
              type="button"
              draggable="true"
              aria-label="拖拽排序"
              @dragstart="startDrag(item, $event)"
              @dragend="draggingId = null"
            >
              <GripVertical :size="18" :stroke-width="2" aria-hidden="true" />
            </button>
            <span class="drag-order">{{ index + 1 }}</span>
            <input
              class="input option-input"
              type="text"
              :value="draftOf(item)"
              :placeholder="activeKey === 'variety' ? '例如 AB 或 BC' : '例如 南宁海吉星市场'"
              :disabled="isSaving(item)"
              :aria-label="`${activeField.label}选项值`"
              @input="onDraftInput(item, $event)"
              @blur="commitValue(item)"
              @keydown.enter.prevent="blurInput($event)"
            />
            <label
              class="tag option-switch"
              :class="item.is_active ? 'success' : 'danger'"
              :title="item.is_active ? '取消勾选即停用' : '勾选即启用'"
            >
              <input
                v-model="item.is_active"
                type="checkbox"
                :disabled="isSaving(item)"
                :aria-label="`${item.is_active ? '停用' : '启用'}${activeField.label}选项`"
                @change="toggleActive(item, $event)"
              />
              <span>{{ item.is_active ? '启用' : '停用' }}</span>
            </label>
            <div class="field-option-actions">
              <button class="table-action danger" type="button" :disabled="isSaving(item)" @click="removeOption(item)">
                <Trash2 :size="15" :stroke-width="2" aria-hidden="true" />删除
              </button>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">暂无{{ activeField.label }}选项</div>
        <p v-if="reordering" class="field-hint">正在保存排序…</p>
      </main>
    </div>

    <div v-if="showModal" class="drawer-mask" @click.self="showModal = false">
      <div class="drawer" role="dialog" aria-modal="true" aria-label="录单字段编辑">
        <div class="drawer-header">
          <div class="drawer-title">新增{{ activeField.label }}选项</div>
          <button class="link-button" @click="showModal = false">关闭</button>
        </div>
        <div class="drawer-body">
          <div class="field">
            <label>选项值</label>
            <input
              v-model="form.value"
              class="input"
              :placeholder="activeField.key === 'variety' ? '例如 G' : '例如 南宁海吉星市场'"
            />
          </div>
          <div class="field checkbox-row">
            <input id="entry-option-active" v-model="form.is_active" type="checkbox" />
            <label for="entry-option-active">启用选项</label>
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
.field-config-shell {
  display: grid;
  grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);
  gap: 1rem;
  min-width: 0;
}

.field-tree {
  align-self: start;
  padding: 0;
  overflow: hidden;
}

.field-tree-head {
  display: grid;
  gap: .18rem;
  padding: 1rem;
  border-bottom: 1px solid var(--line-strong);
}

.field-tree-head strong {
  font-size: 1.05rem;
}

.field-tree-head span {
  color: var(--muted);
  font-size: .85rem;
  line-height: 1.5;
}

.field-tree-group {
  display: grid;
  gap: .18rem;
  padding: .71rem .59rem;
  border-bottom: 1px solid var(--line);
}

.field-tree-group:last-child {
  border-bottom: 0;
}

.field-tree-group-title {
  padding: .35rem .59rem;
  color: var(--muted);
  font-size: .82rem;
  font-weight: 800;
}

.field-tree-node {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: .59rem;
  width: 100%;
  min-height: 2.71rem;
  padding: .53rem .71rem;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--ink);
  text-align: left;
  font: inherit;
}

.field-tree-node:hover {
  background: var(--surface-soft);
}

.field-tree-node.active {
  border-color: var(--primary);
  background: var(--primary-soft);
  color: var(--primary-dark);
  font-weight: 800;
}

.field-tree-node small {
  color: var(--muted);
  font-size: .78rem;
}

.field-tree-node.active small {
  color: var(--primary-dark);
}

.field-config-main {
  min-width: 0;
}

.field-config-main .toolbar {
  align-items: flex-start;
}

.field-hint {
  margin: .35rem 0 0;
  color: var(--muted);
  font-size: .88rem;
  line-height: 1.5;
}

.field-option-list {
  display: grid;
  gap: .41rem;
  padding: .18rem 0;
}

.field-option-row {
  display: grid;
  grid-template-columns: auto auto minmax(0, 1fr) auto auto;
  align-items: center;
  gap: .59rem;
  min-width: 0;
  padding: .59rem .71rem;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: var(--surface);
}

.field-option-row:hover {
  border-color: var(--line-strong);
}

.field-option-row.dragging {
  opacity: .45;
}

.drag-handle {
  display: inline-flex;
  min-width: 2.35rem;
  min-height: 2.35rem;
  align-items: center;
  justify-content: center;
  border: 0;
  background: transparent;
  color: var(--muted);
  cursor: grab;
}

.drag-order {
  min-width: 1.35rem;
  color: var(--muted);
  font-size: .85rem;
  font-weight: 800;
  text-align: right;
}

.option-input {
  min-width: 0;
  min-height: 2.35rem;
  padding: 0 .59rem;
}

.option-switch {
  display: inline-flex;
  align-items: center;
  gap: .35rem;
  cursor: pointer;
  white-space: nowrap;
}

.option-switch input {
  width: 1.06rem;
  height: 1.06rem;
  accent-color: var(--primary);
  cursor: pointer;
}

.option-switch input:disabled,
.field-option-row.saving .option-input {
  cursor: progress;
  opacity: .6;
}

.field-option-row.saving {
  border-color: var(--primary);
}

.field-option-actions {
  display: flex;
  justify-content: flex-end;
  gap: .18rem;
}

@media (max-width: 820px) {
  .field-config-shell {
    grid-template-columns: 1fr;
  }

  .field-tree {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: .35rem .59rem;
  }

  .field-tree-head,
  .field-tree-group {
    display: contents;
  }

  .field-tree-group-title {
    width: 100%;
    margin-top: .35rem;
  }

  .field-tree-node {
    width: auto;
  }
}
</style>
