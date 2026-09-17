<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Download from '@lucide/vue/dist/esm/icons/download.mjs'
import { get } from '../api/client'
import { hasPermission } from '../auth'
import DataTable, { type DataTableColumn } from '../components/DataTable.vue'
import PaginationBar from '../components/PaginationBar.vue'
import type { ListResponse, LoginLogItem, OperationLogItem } from '../types'

const tab = ref<'login' | 'operation'>('operation')
const loginItems = ref<LoginLogItem[]>([])
const operationItems = ref<OperationLogItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const username = ref('')
const moduleFilter = ref('')
const successFilter = ref<'' | 'true' | 'false'>('')
const error = ref('')
const loading = ref(false)

/** 操作日志与登录日志是两张并列的表，分页条由外层共用，所以只抽列定义。 */
const operationColumns: DataTableColumn<OperationLogItem>[] = [
  { key: 'id', label: 'ID', numeric: true },
  { key: 'username', label: '用户', value: (item) => item.username || '—' },
  { key: 'module', label: '模块' },
  { key: 'action', label: '动作' },
  { key: 'target', label: '对象' },
  { key: 'summary', label: '摘要', value: (item) => item.summary || '—' },
  { key: 'status', label: '结果' },
  { key: 'ip', label: 'IP', value: (item) => item.ip || '—' },
  { key: 'created_at', label: '时间', value: (item) => new Date(item.created_at).toLocaleString() },
]

const loginColumns: DataTableColumn<LoginLogItem>[] = [
  { key: 'id', label: 'ID', numeric: true },
  { key: 'username', label: '用户', value: (item) => item.username || '—' },
  { key: 'success', label: '结果' },
  { key: 'message', label: '说明', value: (item) => item.message || '—' },
  { key: 'ip', label: 'IP', value: (item) => item.ip || '—' },
  { key: 'created_at', label: '时间', value: (item) => new Date(item.created_at).toLocaleString() },
]

const targetLabel = (item: OperationLogItem) => `${item.target_type}${item.target_id ? `#${item.target_id}` : ''}`

async function loadLogin() {
  loading.value = true
  error.value = ''
  try {
    const params = new URLSearchParams({ page: String(page.value), page_size: String(pageSize.value) })
    if (username.value) params.set('username', username.value)
    if (successFilter.value !== '') params.set('success', successFilter.value)
    const data = await get<ListResponse<LoginLogItem>>(`/api/admin/logs/login?${params}`)
    loginItems.value = data.items
    total.value = data.total
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function loadOperations() {
  loading.value = true
  error.value = ''
  try {
    const params = new URLSearchParams({ page: String(page.value), page_size: String(pageSize.value) })
    if (username.value) params.set('username', username.value)
    if (moduleFilter.value) params.set('module', moduleFilter.value)
    const data = await get<ListResponse<OperationLogItem>>(`/api/admin/logs/operations?${params}`)
    operationItems.value = data.items
    total.value = data.total
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function changeTab(next: 'login' | 'operation') {
  tab.value = next
  page.value = 1
  if (next === 'login') await loadLogin()
  else await loadOperations()
}

function exportCsv(path: string) {
  window.location.href = path
}

onMounted(loadOperations)
</script>

<template>
  <section class="page-stack">
    <div class="tabs">
      <button :class="{ active: tab === 'operation' }" @click="changeTab('operation')">操作日志</button>
      <button :class="{ active: tab === 'login' }" @click="changeTab('login')">登录日志</button>
    </div>

    <div class="list-card">
      <div class="toolbar">
        <input v-model="username" class="input" style="max-width: 220px" placeholder="用户名" @keyup.enter="page = 1; tab === 'operation' ? loadOperations() : loadLogin()" />
        <select v-if="tab === 'operation'" v-model="moduleFilter" class="select" style="max-width: 160px" @change="page = 1; loadOperations()">
          <option value="">全部模块</option>
          <option value="user">user</option>
          <option value="role">role</option>
          <option value="menu">menu</option>
          <option value="permission">permission</option>
          <option value="config">config</option>
        </select>
        <select v-if="tab === 'login'" v-model="successFilter" class="select" style="max-width: 140px" @change="page = 1; loadLogin()">
          <option value="">全部结果</option>
          <option value="true">成功</option>
          <option value="false">失败</option>
        </select>
        <button class="secondary-button" @click="page = 1; tab === 'operation' ? loadOperations() : loadLogin()">查询</button>
        <button v-if="hasPermission('admin:log:export') && tab === 'operation'" class="secondary-button" @click="exportCsv('/api/admin/logs/operations.csv')">
          <Download :size="16" :stroke-width="2" aria-hidden="true" />
          导出操作日志
        </button>
        <button v-if="hasPermission('admin:log:export') && tab === 'login'" class="secondary-button" @click="exportCsv('/api/admin/logs/login.csv')">
          <Download :size="16" :stroke-width="2" aria-hidden="true" />
          导出登录日志
        </button>
      </div>

    <p v-if="error" class="error">{{ error }}</p>

    <DataTable
      v-if="tab === 'operation'"
      :columns="operationColumns"
      :rows="operationItems"
      :row-key="(item) => item.id"
      caption="操作日志列表"
      min-width="1080px"
      :empty-text="loading ? '正在加载…' : '暂无操作日志'"
    >
      <template #cell-target="{ row }">
        {{ targetLabel(row) }}
      </template>
      <template #cell-status="{ row }">
        <span class="tag" :class="row.status === 'success' ? 'success' : 'danger'">{{ row.status }}</span>
      </template>
    </DataTable>

    <DataTable
      v-if="tab === 'login'"
      :columns="loginColumns"
      :rows="loginItems"
      :row-key="(item) => item.id"
      caption="登录日志列表"
      min-width="820px"
      :empty-text="loading ? '正在加载…' : '暂无登录日志'"
    >
      <template #cell-success="{ row }">
        <span class="tag" :class="row.success ? 'success' : 'danger'">{{ row.success ? '成功' : '失败' }}</span>
      </template>
    </DataTable>

      <PaginationBar
        v-model:page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-size-options="[10, 20, 50, 100]"
        @change="tab === 'operation' ? loadOperations() : loadLogin()"
      />
    </div>
  </section>
</template>
