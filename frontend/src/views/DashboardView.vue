<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import RefreshCw from '@lucide/vue/dist/esm/icons/refresh-cw.mjs'
import { get } from '../api/client'
import type { DashboardStats } from '../types'

const stats = ref<DashboardStats | null>(null)
const loading = ref(true)
const error = ref('')

const importTotal = computed(() => {
  if (!stats.value) return 0
  return Object.values(stats.value.import_status).reduce((sum, value) => sum + value, 0)
})

const issueTotal = computed(() => {
  if (!stats.value) return 0
  return Object.values(stats.value.issue_severity).reduce((sum, value) => sum + value, 0)
})

const maxLoginValue = computed(() => Math.max(1, ...stats.value?.login_trend_7d.map((item) => item.value) ?? [1]))
const maxRoleValue = computed(() => Math.max(1, ...stats.value?.role_distribution.map((item) => item.value) ?? [1]))
const maxGradeValue = computed(() => Math.max(1, ...stats.value?.grade_distribution.map((item) => item.value) ?? [1]))
const maxFruitValue = computed(() => Math.max(1, ...stats.value?.fruit_type_distribution.map((item) => item.value) ?? [1]))

const statusLabels: Record<string, string> = {
  success: '成功',
  pending: '待处理',
  conflict: '冲突',
  failed: '失败',
  warning: '警告',
  partial: '部分成功',
  unknown: '未知',
}

const severityLabels: Record<string, string> = {
  error: '错误',
  warning: '警告',
  info: '提示',
  unknown: '未知',
}

function formatTime(value: string) {
  return new Date(value).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatShortDate(value: string) {
  return value.slice(5).replace('-', '/')
}

function formatAmount(value: number) {
  if (value >= 10000) return `${(value / 10000).toFixed(2)} 万`
  return value.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

function formatDateRange(start: string | null, end: string | null) {
  if (!start && !end) return '暂无销售日期'
  if (start === end) return formatShortDate(start || '')
  return `${start ? formatShortDate(start) : '—'} ~ ${end ? formatShortDate(end) : '—'}`
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    stats.value = await get<DashboardStats>('/api/admin/dashboard/stats')
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <section class="page-stack dashboard-page">
    <p v-if="error" class="error">{{ error }}</p>
    <div v-if="loading && !stats" class="empty-state">正在加载看板数据...</div>

    <template v-if="stats">
      <div class="quick-actions">
        <RouterLink class="quick-action" to="/admin/users">
          <strong>{{ stats.user_total }}</strong>
          <span>管理用户</span>
        </RouterLink>
        <RouterLink class="quick-action" to="/admin/roles">
          <strong>{{ stats.role_total }}</strong>
          <span>角色授权</span>
        </RouterLink>
        <RouterLink class="quick-action" to="/admin/menus">
          <strong>{{ stats.menu_total }}</strong>
          <span>菜单结构</span>
        </RouterLink>
        <RouterLink class="quick-action" to="/admin/data">
          <strong>{{ stats.import_total }}</strong>
          <span>业务数据</span>
        </RouterLink>
        <RouterLink class="quick-action" to="/admin/logs">
          <strong>{{ stats.login_total_7d }}</strong>
          <span>近 7 日登录</span>
        </RouterLink>
        <button class="quick-action dashboard-refresh-action" type="button" @click="load">
          <RefreshCw :size="20" :stroke-width="2" aria-hidden="true" />
          <span>刷新数据</span>
        </button>
      </div>

      <div class="dashboard-grid">
        <section class="card stat-card">
          <span class="stat-card-label">用户总数</span>
          <strong class="stat-card-value">{{ stats.user_total }}</strong>
          <span class="stat-card-note">启用 {{ stats.user_active }} · 禁用 {{ stats.user_disabled }}</span>
        </section>
        <section class="card stat-card">
          <span class="stat-card-label">角色</span>
          <strong class="stat-card-value">{{ stats.role_total }}</strong>
          <span class="stat-card-note">启用 {{ stats.role_active }} 个角色</span>
        </section>
        <section class="card stat-card">
          <span class="stat-card-label">权限点</span>
          <strong class="stat-card-value">{{ stats.permission_total }}</strong>
          <span class="stat-card-note">启用 {{ stats.permission_active }} 个权限点</span>
        </section>
        <section class="card stat-card">
          <span class="stat-card-label">AI 缓存</span>
          <strong class="stat-card-value">{{ stats.ai_cache_total }}</strong>
          <span class="stat-card-note">当前已缓存分析结论</span>
        </section>
        <section class="card stat-card">
          <span class="stat-card-label">销售记录</span>
          <strong class="stat-card-value">{{ stats.sale_record_total }}</strong>
          <span class="stat-card-note">累计明细 {{ formatDateRange(stats.sales_date_start, stats.sales_date_end) }}</span>
        </section>
        <section class="card stat-card">
          <span class="stat-card-label">销售金额</span>
          <strong class="stat-card-value">{{ formatAmount(stats.total_sales_amount) }}</strong>
          <span class="stat-card-note">所有销售记录金额合计</span>
        </section>
        <section class="card stat-card">
          <span class="stat-card-label">源文件</span>
          <strong class="stat-card-value">{{ stats.source_file_total }}</strong>
          <span class="stat-card-note">原始文件归档数</span>
        </section>
        <section class="card stat-card">
          <span class="stat-card-label">结算摘要</span>
          <strong class="stat-card-value">{{ stats.settlement_total }}</strong>
          <span class="stat-card-note">最近导入 {{ stats.latest_import_at ? formatTime(stats.latest_import_at) : '—' }}</span>
        </section>
      </div>

      <div class="dashboard-grid dashboard-grid-wide">
        <section class="card dashboard-panel">
          <div class="panel-title">
            <h2>近 7 日登录趋势</h2>
            <span>成功 {{ stats.login_total_7d }} · 失败 {{ stats.login_failed_7d }}</span>
          </div>
          <div class="trend-chart">
            <div v-for="item in stats.login_trend_7d" :key="item.date" class="trend-column">
              <span class="trend-value">{{ item.value }}</span>
              <div class="trend-bar" :style="{ height: `${Math.max(4, (item.value / maxLoginValue) * 100)}%` }"></div>
              <span class="trend-label">{{ formatShortDate(item.date) }}</span>
            </div>
          </div>
        </section>

        <section class="card dashboard-panel">
          <div class="panel-title">
            <h2>导入批次状态</h2>
            <span>共 {{ importTotal }} 批</span>
          </div>
          <div class="bar-list">
            <div v-for="(value, key) in stats.import_status" :key="key" class="bar-row">
              <div class="bar-row-head">
                <span>{{ statusLabels[key] || key }}</span>
                <strong>{{ value }}</strong>
              </div>
              <div class="bar-track">
                <span class="bar-fill" :style="{ width: `${importTotal ? (value / importTotal) * 100 : 0}%` }"></span>
              </div>
            </div>
            <div v-if="!importTotal" class="empty-state">暂无导入数据</div>
          </div>
        </section>

        <section class="card dashboard-panel">
          <div class="panel-title">
            <h2>数据问题严重度</h2>
            <span>共 {{ issueTotal }} 条</span>
          </div>
          <div class="bar-list">
            <div v-for="(value, key) in stats.issue_severity" :key="key" class="bar-row">
              <div class="bar-row-head">
                <span>{{ severityLabels[key] || key }}</span>
                <strong>{{ value }}</strong>
              </div>
              <div class="bar-track">
                <span class="bar-fill severity" :class="key" :style="{ width: `${issueTotal ? (value / issueTotal) * 100 : 0}%` }"></span>
              </div>
            </div>
            <div v-if="!issueTotal" class="empty-state">暂无数据问题</div>
          </div>
        </section>

        <section class="card dashboard-panel">
          <div class="panel-title">
            <h2>角色用户分布</h2>
            <span>按绑定用户数</span>
          </div>
          <div class="bar-list">
            <div v-for="item in stats.role_distribution" :key="item.name" class="bar-row">
              <div class="bar-row-head">
                <span>{{ item.name }}</span>
                <strong>{{ item.value }}</strong>
              </div>
              <div class="bar-track">
                <span class="bar-fill" :style="{ width: `${(item.value / maxRoleValue) * 100}%` }"></span>
              </div>
            </div>
            <div v-if="!stats.role_distribution.length" class="empty-state">暂无角色绑定数据</div>
          </div>
        </section>

        <section class="card dashboard-panel">
          <div class="panel-title">
            <h2>销售等级分布</h2>
            <span>按销售明细数</span>
          </div>
          <div class="bar-list">
            <div v-for="item in stats.grade_distribution" :key="item.name" class="bar-row">
              <div class="bar-row-head">
                <span>{{ item.name }} 级</span>
                <strong>{{ item.value }}</strong>
              </div>
              <div class="bar-track">
                <span class="bar-fill" :style="{ width: `${(item.value / maxGradeValue) * 100}%` }"></span>
              </div>
            </div>
            <div v-if="!stats.grade_distribution.length" class="empty-state">暂无等级数据</div>
          </div>
        </section>

        <section class="card dashboard-panel">
          <div class="panel-title">
            <h2>果品类型分布</h2>
            <span>按销售明细数</span>
          </div>
          <div class="bar-list">
            <div v-for="item in stats.fruit_type_distribution" :key="item.name" class="bar-row">
              <div class="bar-row-head">
                <span>{{ item.name }}</span>
                <strong>{{ item.value }}</strong>
              </div>
              <div class="bar-track">
                <span class="bar-fill" :style="{ width: `${(item.value / maxFruitValue) * 100}%` }"></span>
              </div>
            </div>
            <div v-if="!stats.fruit_type_distribution.length" class="empty-state">暂无果品数据</div>
          </div>
        </section>
      </div>

      <div class="dashboard-grid dashboard-grid-wide">
        <section class="card dashboard-panel">
          <div class="panel-title">
            <h2>最近操作</h2>
            <RouterLink class="text-link" to="/admin/logs">查看全部</RouterLink>
          </div>
          <div class="activity-list">
            <div v-for="item in stats.recent_operations" :key="`operation-${item.id}`" class="activity-item">
              <span class="activity-dot"></span>
              <div class="activity-body">
                <strong>{{ item.username || '系统' }} · {{ item.summary || `${item.module}/${item.action}` }}</strong>
                <span>{{ formatTime(item.created_at) }}</span>
              </div>
              <span class="tag" :class="item.status === 'success' ? 'success' : 'danger'">{{ item.status }}</span>
            </div>
            <div v-if="!stats.recent_operations.length" class="empty-state">暂无操作记录</div>
          </div>
        </section>

        <section class="card dashboard-panel">
          <div class="panel-title">
            <h2>最近登录</h2>
            <RouterLink class="text-link" to="/admin/logs">查看全部</RouterLink>
          </div>
          <div class="activity-list">
            <div v-for="item in stats.recent_logins" :key="`login-${item.id}`" class="activity-item">
              <span class="activity-dot" :class="{ success: item.success, danger: !item.success }"></span>
              <div class="activity-body">
                <strong>{{ item.username || '未知用户' }}</strong>
                <span>{{ item.message || (item.success ? '登录成功' : '登录失败') }} · {{ item.ip || '未知 IP' }}</span>
              </div>
              <span>{{ formatTime(item.created_at) }}</span>
            </div>
            <div v-if="!stats.recent_logins.length" class="empty-state">暂无登录记录</div>
          </div>
        </section>
      </div>
    </template>
  </section>
</template>
