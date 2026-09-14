<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Download from '@lucide/vue/dist/esm/icons/download.mjs'
import { get } from '../api/client'
import { hasPermission } from '../auth'
import PaginationBar from '../components/PaginationBar.vue'
import type { ListResponse, LoginLogItem, OperationLogItem } from '../types'

const tab = ref<'login' | 'operation'>('operation')
const loginItems = ref<LoginLogItem[]>([])
const operationItems = ref<OperationLogItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const username = ref('')
const moduleFilter = ref('')
const successFilter = ref<'' | 'true' | 'false'>('')
const error = ref('')
const loading = ref(false)

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

    <div v-if="tab === 'operation'" class="table-wrap">
    <table class="table">
      <thead>
        <tr>
          <th>ID</th>
          <th>用户</th>
          <th>模块</th>
          <th>动作</th>
          <th>对象</th>
          <th>摘要</th>
          <th>结果</th>
          <th>IP</th>
          <th>时间</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in operationItems" :key="item.id">
          <td>{{ item.id }}</td>
          <td>{{ item.username || '—' }}</td>
          <td>{{ item.module }}</td>
          <td>{{ item.action }}</td>
          <td>{{ item.target_type }}{{ item.target_id ? `#${item.target_id}` : '' }}</td>
          <td>{{ item.summary || '—' }}</td>
          <td><span class="tag" :class="item.status === 'success' ? 'success' : 'danger'">{{ item.status }}</span></td>
          <td>{{ item.ip || '—' }}</td>
          <td>{{ new Date(item.created_at).toLocaleString() }}</td>
        </tr>
      </tbody>
    </table>
    </div>
    <div v-if="tab === 'operation' && !loading && !operationItems.length" class="empty-state">暂无操作日志</div>

    <div v-if="tab === 'login'" class="table-wrap">
    <table class="table">
      <thead>
        <tr>
          <th>ID</th>
          <th>用户</th>
          <th>结果</th>
          <th>说明</th>
          <th>IP</th>
          <th>时间</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in loginItems" :key="item.id">
          <td>{{ item.id }}</td>
          <td>{{ item.username || '—' }}</td>
          <td><span class="tag" :class="item.success ? 'success' : 'danger'">{{ item.success ? '成功' : '失败' }}</span></td>
          <td>{{ item.message || '—' }}</td>
          <td>{{ item.ip || '—' }}</td>
          <td>{{ new Date(item.created_at).toLocaleString() }}</td>
        </tr>
      </tbody>
    </table>
    </div>
    <div v-if="tab === 'login' && !loading && !loginItems.length" class="empty-state">暂无登录日志</div>

    <PaginationBar
      v-model:page="page"
      v-model:page-size="pageSize"
      :total="total"
      :page-size-options="[20, 50, 100]"
      @change="tab === 'operation' ? loadOperations() : loadLogin()"
    />
  </section>
</template>
