<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { del, get } from '../api/client'
import { confirmAction, notify } from '../feedback'
import { hasPermission } from '../auth'
import Eye from '@lucide/vue/dist/esm/icons/eye.mjs'
import Trash2 from '@lucide/vue/dist/esm/icons/trash.mjs'
import DataTable, { type DataTableColumn } from '../components/DataTable.vue'
import PaginationBar from '../components/PaginationBar.vue'
import type { AiCacheItem, DataIssueItem, ImportBatchItem, ListResponse } from '../types'

const tab = ref<'imports' | 'issues' | 'ai'>('imports')
const imports = ref<ImportBatchItem[]>([])
const importTotal = ref(0)
const issues = ref<DataIssueItem[]>([])
const issueTotal = ref(0)
const aiItems = ref<AiCacheItem[]>([])
const aiTotal = ref(0)
const selectedBatch = ref<ImportBatchItem | null>(null)
const keyword = ref('')
const status = ref('')
const page = ref(1)
const pageSize = ref(10)
const error = ref('')
const loading = ref(false)
const busyId = ref<number | null>(null)

async function loadImports() {
  loading.value = true
  error.value = ''
  try {
    const params = new URLSearchParams({ page: String(page.value), page_size: String(pageSize.value) })
    if (keyword.value) params.set('keyword', keyword.value)
    if (status.value) params.set('status', status.value)
    const data = await get<ListResponse<ImportBatchItem>>(`/api/admin/data/imports?${params}`)
    imports.value = data.items
    importTotal.value = data.total
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function loadIssues(batchId: number) {
  const data = await get<ListResponse<DataIssueItem>>(`/api/admin/data/imports/${batchId}/issues`)
  issues.value = data.items
  issueTotal.value = data.total
}

async function loadAi() {
  const data = await get<ListResponse<AiCacheItem>>(`/api/admin/data/ai-cache?page=1&page_size=50`)
  aiItems.value = data.items
  aiTotal.value = data.total
}

async function showIssues(batch: ImportBatchItem) {
  selectedBatch.value = batch
  tab.value = 'issues'
  await loadIssues(batch.id)
}

async function deleteAi(item: AiCacheItem) {
  const ok = await confirmAction(`确认删除缓存 ${item.feature}？`, {
    title: '删除 AI 缓存',
    confirmText: '删除',
  })
  if (!ok) return
  busyId.value = item.id
  try {
    await del(`/api/admin/data/ai-cache/${item.id}`)
    notify('缓存已删除')
    await loadAi()
  } catch (err) {
    notify(err instanceof Error ? err.message : '删除失败', 'error')
  } finally {
    busyId.value = null
  }
}

async function changeTab(next: 'imports' | 'issues' | 'ai') {
  tab.value = next
  if (next === 'imports') await loadImports()
  if (next === 'ai') await loadAi()
}

/** 三个页签各一张表，列固定、操作列走插槽。 */
const importColumns: DataTableColumn<ImportBatchItem>[] = [
  { key: 'id', label: 'ID', numeric: true },
  { key: 'merchant_no', label: '商号', emphasis: true, rowHeader: true, value: (item) => item.merchant_no_normalized || item.merchant_no },
  { key: 'order_no', label: '单号', value: (item) => item.order_no_normalized || item.order_no || '—' },
  { key: 'container_no', label: '柜号', value: (item) => item.container_no || '—' },
  { key: 'file_name', label: '文件', value: (item) => item.file_name || '—' },
  { key: 'imported_at', label: '导入时间', value: (item) => (item.imported_at ? new Date(item.imported_at).toLocaleString() : '—') },
  { key: 'status', label: '状态' },
  { key: 'counts', label: '成功/警告/失败', value: (item) => `${item.success_count} / ${item.warning_count} / ${item.failure_count}` },
  { key: 'actions', label: '操作' },
]

const issueColumns: DataTableColumn<DataIssueItem>[] = [
  { key: 'row_number', label: '行号', numeric: true, value: (item) => item.row_number ?? '—' },
  { key: 'severity', label: '严重程度' },
  { key: 'issue_type', label: '问题类型' },
  { key: 'field_name', label: '字段', value: (item) => item.field_name || '—' },
  { key: 'message', label: '说明' },
  { key: 'raw_value', label: '原始值', value: (item) => item.raw_value || '—' },
]

const aiColumns: DataTableColumn<AiCacheItem>[] = [
  { key: 'id', label: 'ID', numeric: true },
  { key: 'feature', label: '功能', emphasis: true, rowHeader: true },
  { key: 'model', label: '模型' },
  { key: 'cache_key', label: '缓存键' },
  { key: 'created_at', label: '生成时间', value: (item) => (item.created_at ? new Date(item.created_at).toLocaleString() : '—') },
  { key: 'content', label: '内容' },
  { key: 'actions', label: '操作' },
]

onMounted(loadImports)
</script>

<template>
  <section class="page-stack">
    <div class="tabs">
      <button :class="{ active: tab === 'imports' }" @click="changeTab('imports')">导入批次</button>
      <button :class="{ active: tab === 'issues' }" :disabled="!selectedBatch" @click="changeTab('issues')">数据问题</button>
      <button :class="{ active: tab === 'ai' }" @click="changeTab('ai')">AI 缓存</button>
    </div>

    <div v-if="tab === 'imports'">
      <div class="list-card">
        <div class="toolbar">
          <input v-model="keyword" class="input" style="max-width: 220px" placeholder="商号、单号或文件名" @keyup.enter="page = 1; loadImports()" />
          <select v-model="status" class="select" style="max-width: 160px" @change="page = 1; loadImports()">
            <option value="">全部状态</option>
            <option value="success">成功</option>
            <option value="conflict">冲突</option>
            <option value="pending">待处理</option>
            <option value="failed">失败</option>
          </select>
          <button class="secondary-button" @click="page = 1; loadImports()">查询</button>
        </div>
        <p v-if="error" class="error">{{ error }}</p>
        <DataTable
          :columns="importColumns"
          :rows="imports"
          :row-key="(item) => item.id"
          caption="导入批次列表"
          min-width="1080px"
          :empty-text="loading ? '正在加载…' : '暂无导入批次'"
        >
          <template #cell-status="{ row }">
            <span class="tag" :class="row.status">{{ row.status }}</span>
          </template>
          <template #cell-actions="{ row }">
            <button class="table-action" @click="showIssues(row)"><Eye :size="15" :stroke-width="2" aria-hidden="true" />查看问题</button>
          </template>
          <template #footer>
            <PaginationBar
              v-model:page="page"
              v-model:page-size="pageSize"
              :total="importTotal"
              :page-size-options="[10, 20, 50, 100]"
              @change="loadImports"
            />
          </template>
        </DataTable>
      </div>
    </div>

    <div v-if="tab === 'issues'">
      <div class="toolbar">
        <span>当前批次：{{ selectedBatch?.merchant_no_normalized || selectedBatch?.merchant_no }}</span>
        <span>共 {{ issueTotal }} 条问题</span>
      </div>
      <DataTable
        :columns="issueColumns"
        :rows="issues"
        :row-key="(item) => item.id"
        caption="该批次的数据问题明细"
        min-width="900px"
        bordered
        empty-text="该批次暂无数据问题"
      >
        <template #cell-severity="{ row }">
          <span class="tag" :class="row.severity === 'error' ? 'danger' : 'warning'">{{ row.severity }}</span>
        </template>
      </DataTable>
    </div>

    <div v-if="tab === 'ai'">
      <DataTable
        :columns="aiColumns"
        :rows="aiItems"
        :row-key="(item) => item.id"
        caption="AI 分析缓存列表"
        min-width="980px"
        empty-text="暂无 AI 缓存"
      >
        <template #cell-cache_key="{ row }">
          <code>{{ row.cache_key }}</code>
        </template>
        <template #cell-content="{ row }">
          <span class="ai-cache-content">{{ row.content }}</span>
        </template>
        <template #cell-actions="{ row }">
          <button v-if="hasPermission('admin:data:refresh-cache')" class="table-action danger" :disabled="busyId === row.id" @click="deleteAi(row)"><Trash2 :size="15" :stroke-width="2" aria-hidden="true" />删除</button>
        </template>
      </DataTable>
    </div>
  </section>
</template>

<style scoped>
.danger-text { color: var(--danger); }
/* 缓存内容是长文本，收窄列宽并在单元格内折行，避免整张表被撑开。 */
.ai-cache-content { display: block; max-width: 22rem; overflow-wrap: anywhere; }
</style>
