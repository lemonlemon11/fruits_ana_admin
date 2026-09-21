<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { get, patch } from '../api/client'
import { notify } from '../feedback'
import { hasPermission } from '../auth'
import Pencil from '@lucide/vue/dist/esm/icons/pencil.mjs'
import DataTable, { type DataTableColumn } from '../components/DataTable.vue'

type SettingItem = { key: string; value: string | null; description: string | null; editable: boolean }

const items = ref<SettingItem[]>([])
const editingKey = ref<string | null>(null)
const editValue = ref('')
const error = ref('')
const saving = ref(false)

// 「操作」列只有具备配置修改权限时才出现，所以列定义用 computed。
const columns = computed<DataTableColumn<SettingItem>[]>(() => {
  const base: DataTableColumn<SettingItem>[] = [
    { key: 'key', label: '配置项', emphasis: true, rowHeader: true },
    { key: 'value', label: '值' },
    { key: 'description', label: '说明', value: (item) => item.description || '—' },
  ]
  if (hasPermission('admin:config:update')) base.push({ key: 'actions', label: '操作' })
  return base
})

async function load() {
  error.value = ''
  try {
    const data = await get<{ items: SettingItem[] }>('/api/admin/settings')
    items.value = data.items
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败'
  }
}

function openEdit(item: SettingItem) {
  if (!item.editable) return
  editingKey.value = item.key
  editValue.value = item.value || ''
}

async function save() {
  if (!editingKey.value) return
  saving.value = true
  try {
    await patch(`/api/admin/settings/${editingKey.value}`, { value: editValue.value })
    notify('配置已保存')
    editingKey.value = null
    await load()
  } catch (err) {
    notify(err instanceof Error ? err.message : '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <section class="page-stack">
    <p v-if="error" class="error">{{ error }}</p>

    <DataTable
      :columns="columns"
      :rows="items"
      :row-key="(item) => item.key"
      caption="管理端系统配置列表"
      min-width="720px"
      :empty-text="'暂无配置项'"
    >
      <template #cell-key="{ row }">
        <code>{{ row.key }}</code>
      </template>
      <template #cell-value="{ row }">
        <span v-if="editingKey !== row.key">{{ row.value || '—' }}</span>
        <input v-else v-model="editValue" class="input" />
      </template>
      <template #cell-actions="{ row }">
        <span v-if="!row.editable" style="color: var(--muted)">用户端维护</span>
        <template v-else-if="editingKey !== row.key">
          <button class="table-action" @click="openEdit(row)"><Pencil :size="15" :stroke-width="2" aria-hidden="true" />编辑</button>
        </template>
        <template v-else>
          <button class="primary-button" :disabled="saving" @click="save">{{ saving ? '保存中...' : '保存' }}</button>
          <button class="secondary-button" :disabled="saving" @click="editingKey = null">取消</button>
        </template>
      </template>
    </DataTable>
  </section>
</template>
