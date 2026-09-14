<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { del, get } from '../api/client'
import { confirmAction, notify } from '../feedback'
import { hasPermission } from '../auth'
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
      <div class="table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>商号</th>
            <th>单号</th>
            <th>柜号</th>
            <th>文件</th>
            <th>导入时间</th>
            <th>状态</th>
            <th>成功/警告/失败</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in imports" :key="item.id">
            <td>{{ item.id }}</td>
            <td>{{ item.merchant_no_normalized || item.merchant_no }}</td>
            <td>{{ item.order_no_normalized || item.order_no || '—' }}</td>
            <td>{{ item.container_no || '—' }}</td>
            <td>{{ item.file_name || '—' }}</td>
            <td>{{ item.imported_at ? new Date(item.imported_at).toLocaleString() : '—' }}</td>
            <td><span class="tag" :class="item.status">{{ item.status }}</span></td>
            <td>{{ item.success_count }} / {{ item.warning_count }} / {{ item.failure_count }}</td>
            <td><button class="link-button" @click="showIssues(item)">查看问题</button></td>
          </tr>
        </tbody>
      </table>
      </div>
      <div class="empty-state" v-if="!loading && !imports.length">暂无导入批次</div>
      <div class="pagination">
        <button class="secondary-button" :disabled="page <= 1" @click="page--; loadImports()">上一页</button>
        <span>{{ page }}</span>
        <button class="secondary-button" :disabled="page * pageSize >= importTotal" @click="page++; loadImports()">下一页</button>
      </div>
    </div>

    <div v-if="tab === 'issues'">
      <div class="toolbar">
        <span>当前批次：{{ selectedBatch?.merchant_no_normalized || selectedBatch?.merchant_no }}</span>
        <span>共 {{ issueTotal }} 条问题</span>
      </div>
      <div class="table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th>行号</th>
            <th>严重程度</th>
            <th>问题类型</th>
            <th>字段</th>
            <th>说明</th>
            <th>原始值</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in issues" :key="item.id">
            <td>{{ item.row_number ?? '—' }}</td>
            <td><span class="tag" :class="item.severity === 'error' ? 'danger' : 'warning'">{{ item.severity }}</span></td>
            <td>{{ item.issue_type }}</td>
            <td>{{ item.field_name || '—' }}</td>
            <td>{{ item.message }}</td>
            <td>{{ item.raw_value || '—' }}</td>
          </tr>
        </tbody>
      </table>
      </div>
      <div class="empty-state" v-if="!issues.length">该批次暂无数据问题</div>
    </div>

    <div v-if="tab === 'ai'">
      <div class="table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>功能</th>
            <th>模型</th>
            <th>缓存键</th>
            <th>生成时间</th>
            <th>内容</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in aiItems" :key="item.id">
            <td>{{ item.id }}</td>
            <td>{{ item.feature }}</td>
            <td>{{ item.model }}</td>
            <td><code>{{ item.cache_key }}</code></td>
            <td>{{ item.created_at ? new Date(item.created_at).toLocaleString() : '—' }}</td>
            <td style="max-width: 360px">{{ item.content }}</td>
            <td>
              <button v-if="hasPermission('admin:data:refresh-cache')" class="link-button danger-text" :disabled="busyId === item.id" @click="deleteAi(item)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
      </div>
      <div class="empty-state" v-if="!aiItems.length">暂无 AI 缓存</div>
    </div>
  </section>
</template>

<style scoped>
.danger-text { color: var(--danger); }
</style>
