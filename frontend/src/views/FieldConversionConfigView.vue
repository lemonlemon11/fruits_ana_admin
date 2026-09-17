<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import GripVertical from '@lucide/vue/dist/esm/icons/grip-vertical.mjs'
import Plus from '@lucide/vue/dist/esm/icons/plus.mjs'
import Trash2 from '@lucide/vue/dist/esm/icons/trash.mjs'
import { del, get, patch, post, put } from '../api/client'
import { confirmAction, notify } from '../feedback'
import { useEscapeClose } from '../composables/useEscapeClose'
import type { FieldConversionRule, FieldConversionRuleList } from '../types'

const items = ref<FieldConversionRule[]>([])
const error = ref('')
const saving = ref(false)
const reordering = ref(false)
const draggingId = ref<number | null>(null)
const showModal = ref(false)
const drafts = ref<Record<number, Partial<FieldConversionRule>>>({})
const savingIds = ref<number[]>([])
const form = reactive({
  source_value: '',
  target_value: 'C',
  description: '',
  is_active: true,
})

useEscapeClose(() => showModal.value, () => {
  showModal.value = false
})

function draftOf(item: FieldConversionRule, key: 'source_value' | 'target_value' | 'description') {
  return drafts.value[item.id]?.[key] ?? item[key] ?? ''
}

function setDraft(item: FieldConversionRule, key: 'source_value' | 'target_value' | 'description', value: string) {
  drafts.value[item.id] = { ...drafts.value[item.id], [key]: value }
}

function startSaving(item: FieldConversionRule) {
  if (!savingIds.value.includes(item.id)) savingIds.value = [...savingIds.value, item.id]
}

function endSaving(item: FieldConversionRule) {
  savingIds.value = savingIds.value.filter((id) => id !== item.id)
}

function isSaving(item: FieldConversionRule) {
  return savingIds.value.includes(item.id)
}

function validGrade(value: string) {
  return /^[A-Z]{1,4}$/.test(value.trim().toUpperCase())
}

async function load() {
  error.value = ''
  try {
    const data = await get<FieldConversionRuleList>('/api/admin/field-conversion-rules?field=grade')
    items.value = data.items
    drafts.value = {}
    savingIds.value = []
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '加载失败'
  }
}

function openCreate() {
  form.source_value = ''
  form.target_value = 'C'
  form.description = ''
  form.is_active = true
  showModal.value = true
}

async function createRule() {
  const source = form.source_value.trim().toUpperCase()
  const target = form.target_value.trim().toUpperCase()
  if (!validGrade(source) || !validGrade(target)) {
    notify('原始值和目标值必须由 1-4 个大写英文字母组成', 'error')
    return
  }
  saving.value = true
  try {
    await post('/api/admin/field-conversion-rules', {
      field_key: 'grade',
      source_value: source,
      target_value: target,
      sort_order: items.value.length,
      is_active: form.is_active,
      description: form.description || null,
    })
    notify('转换规则已创建')
    showModal.value = false
    await load()
  } catch (caught) {
    notify(caught instanceof Error ? caught.message : '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

async function commit(item: FieldConversionRule, key: 'source_value' | 'target_value' | 'description') {
  if (isSaving(item)) return
  const raw = draftOf(item, key)
  const next = key === 'description' ? raw : raw.trim().toUpperCase()
  if (next === (item[key] ?? '')) {
    drafts.value[item.id] = { ...drafts.value[item.id], [key]: next }
    return
  }
  if (key !== 'description' && !validGrade(next)) {
    drafts.value[item.id] = { ...drafts.value[item.id], [key]: item[key] ?? '' }
    notify('原始值和目标值必须由 1-4 个大写英文字母组成', 'error')
    return
  }
  startSaving(item)
  try {
    const payload = key === 'description' ? { description: next || null } : { [key]: next }
    await patch(`/api/admin/field-conversion-rules/${item.id}`, payload)
    item[key] = next
    drafts.value[item.id] = { ...drafts.value[item.id], [key]: next }
    notify('转换规则已更新')
  } catch (caught) {
    drafts.value[item.id] = { ...drafts.value[item.id], [key]: item[key] ?? '' }
    notify(caught instanceof Error ? caught.message : '保存失败', 'error')
  } finally {
    endSaving(item)
  }
}

async function toggleActive(item: FieldConversionRule, event: Event) {
  if (isSaving(item)) return
  const next = (event.target as HTMLInputElement).checked
  startSaving(item)
  try {
    await patch(`/api/admin/field-conversion-rules/${item.id}`, { is_active: next })
    item.is_active = next
    notify(next ? '转换规则已启用' : '转换规则已停用')
  } catch (caught) {
    item.is_active = !next
    notify(caught instanceof Error ? caught.message : '保存失败', 'error')
  } finally {
    endSaving(item)
  }
}

async function removeRule(item: FieldConversionRule) {
  const ok = await confirmAction(`确认删除 ${item.source_value} → ${item.target_value}？`, {
    title: '删除转换规则',
    confirmText: '删除',
  })
  if (!ok) return
  try {
    await del(`/api/admin/field-conversion-rules/${item.id}`)
    notify('转换规则已删除')
    await load()
  } catch (caught) {
    notify(caught instanceof Error ? caught.message : '删除失败', 'error')
  }
}

function startDrag(item: FieldConversionRule, event: DragEvent) {
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
    const data = await put<FieldConversionRuleList>('/api/admin/field-conversion-rules/reorder', {
      field_key: 'grade',
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

function blurInput(event: Event) {
  ;(event.target as HTMLElement).blur()
}

onMounted(load)
</script>

<template>
  <section class="page-stack">
    <div class="field-config-main list-card">
      <div class="toolbar">
        <div>
          <h2>品种统计转换</h2>
          <p class="field-hint">界面继续显示用户原始品种；转换规则只影响看板、统计和导出。</p>
          <p class="field-hint">默认规则：BC → C。可直接改原值、目标值、说明或启用状态，失焦即保存。</p>
        </div>
        <button class="primary-button toolbar-action" type="button" @click="openCreate">
          <Plus :size="16" :stroke-width="2" aria-hidden="true" />新增转换规则
        </button>
      </div>

      <p v-if="error" class="error">{{ error }}</p>

      <div v-if="items.length" class="conversion-list" :class="{ 'is-dragging': draggingId !== null }">
        <div
          v-for="(item, index) in items"
          :key="item.id"
          class="conversion-row"
          :class="{ dragging: draggingId === item.id, saving: isSaving(item) }"
          :aria-busy="isSaving(item)"
          @dragover.prevent
          @drop="onDrop(item.id)"
        >
          <button class="drag-handle" type="button" draggable="true" aria-label="拖拽排序" @dragstart="startDrag(item, $event)" @dragend="draggingId = null">
            <GripVertical :size="18" :stroke-width="2" aria-hidden="true" />
          </button>
          <span class="drag-order">{{ index + 1 }}</span>
          <div class="conversion-value">
            <input
              class="input"
              :value="draftOf(item, 'source_value')"
              aria-label="原始品种"
              :disabled="isSaving(item)"
              @input="setDraft(item, 'source_value', ($event.target as HTMLInputElement).value)"
              @blur="commit(item, 'source_value')"
              @keydown.enter.prevent="blurInput($event)"
            />
            <span>→</span>
            <input
              class="input"
              :value="draftOf(item, 'target_value')"
              aria-label="统计品种"
              :disabled="isSaving(item)"
              @input="setDraft(item, 'target_value', ($event.target as HTMLInputElement).value)"
              @blur="commit(item, 'target_value')"
              @keydown.enter.prevent="blurInput($event)"
            />
          </div>
          <input
            class="input description-input"
            :value="draftOf(item, 'description')"
            placeholder="说明"
            aria-label="规则说明"
            :disabled="isSaving(item)"
            @input="setDraft(item, 'description', ($event.target as HTMLInputElement).value)"
            @blur="commit(item, 'description')"
            @keydown.enter.prevent="blurInput($event)"
          />
          <label class="tag option-switch" :class="item.is_active ? 'success' : 'danger'">
            <input v-model="item.is_active" type="checkbox" :disabled="isSaving(item)" :aria-label="item.is_active ? '停用规则' : '启用规则'" @change="toggleActive(item, $event)" />
            <span>{{ item.is_active ? '启用' : '停用' }}</span>
          </label>
          <button class="table-action danger" type="button" :disabled="isSaving(item)" @click="removeRule(item)">
            <Trash2 :size="15" :stroke-width="2" aria-hidden="true" />删除
          </button>
        </div>
      </div>
      <div v-else class="empty-state">暂无转换规则</div>
      <p v-if="reordering" class="field-hint">正在保存排序…</p>
    </div>

    <div v-if="showModal" class="drawer-mask" @click.self="showModal = false">
      <div class="drawer" role="dialog" aria-modal="true" aria-label="新增转换规则">
        <div class="drawer-header">
          <div class="drawer-title">新增转换规则</div>
          <button class="link-button" @click="showModal = false">关闭</button>
        </div>
        <div class="drawer-body">
          <div class="field">
            <label>原始品种</label>
            <input v-model="form.source_value" class="input" placeholder="例如 BC" />
          </div>
          <div class="field">
            <label>统计品种</label>
            <input v-model="form.target_value" class="input" placeholder="例如 C" />
          </div>
          <div class="field">
            <label>说明</label>
            <input v-model="form.description" class="input" placeholder="例如 BC 统计归 C" />
          </div>
          <div class="field">
            <label class="tag option-switch" :class="form.is_active ? 'success' : 'danger'">
              <input v-model="form.is_active" type="checkbox" />
              <span>{{ form.is_active ? '启用' : '停用' }}</span>
            </label>
          </div>
        </div>
        <div class="drawer-actions">
          <button class="secondary-button" type="button" @click="showModal = false">取消</button>
          <button class="primary-button" type="button" :disabled="saving" @click="createRule">保存</button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.field-config-main { min-width: 0; }
.conversion-list { display: grid; gap: .5rem; }
.conversion-row {
  display: grid;
  grid-template-columns: 2rem 2rem minmax(0, 1.2fr) minmax(0, 1fr) auto auto;
  gap: .6rem;
  align-items: center;
  padding: .7rem;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: var(--surface);
}
.conversion-row.saving { opacity: .72; }
.conversion-row.dragging { opacity: .45; }
.drag-handle { display: inline-grid; place-items: center; padding: 0; border: 0; background: transparent; color: var(--muted); cursor: grab; }
.drag-order { color: var(--muted); font-size: .9rem; font-weight: 700; text-align: center; }
.conversion-value { display: grid; grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr); gap: .5rem; align-items: center; color: var(--muted); }
.description-input { min-width: 0; }
.input { width: 100%; min-height: 2.5rem; padding: .4rem .5rem; border: 1px solid var(--line-strong); border-radius: var(--radius-sm); background: #fff; color: var(--ink); font: inherit; }
.table-action { display: inline-flex; align-items: center; gap: .3rem; min-height: 2.2rem; padding: .25rem .5rem; border: 0; background: transparent; font-weight: 800; cursor: pointer; }
.table-action.danger { color: #8e3028; }
@media (max-width: 780px) {
  .conversion-row { grid-template-columns: 2rem 2rem 1fr auto auto; }
  .conversion-value { grid-column: 3 / 6; grid-row: 1; }
  .description-input { grid-column: 3 / 5; }
  .option-switch { justify-self: start; }
  .table-action { justify-self: end; }
}
</style>
