<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import ArrowUp from '@lucide/vue/dist/esm/icons/arrow-up.mjs'
import Bell from '@lucide/vue/dist/esm/icons/bell.mjs'
import Clock3 from '@lucide/vue/dist/esm/icons/clock-3.mjs'
import Database from '@lucide/vue/dist/esm/icons/database.mjs'
import FolderTree from '@lucide/vue/dist/esm/icons/folder-tree.mjs'
import KeyRound from '@lucide/vue/dist/esm/icons/key-round.mjs'
import LayoutDashboard from '@lucide/vue/dist/esm/icons/layout-dashboard.mjs'
import LogOut from '@lucide/vue/dist/esm/icons/log-out.mjs'
import PanelLeftClose from '@lucide/vue/dist/esm/icons/panel-left-close.mjs'
import PanelLeftOpen from '@lucide/vue/dist/esm/icons/panel-left-open.mjs'
import ScrollText from '@lucide/vue/dist/esm/icons/scroll-text.mjs'
import Settings from '@lucide/vue/dist/esm/icons/settings.mjs'
import ShieldCheck from '@lucide/vue/dist/esm/icons/shield-check.mjs'
import Users from '@lucide/vue/dist/esm/icons/users.mjs'
import X from '@lucide/vue/dist/esm/icons/x.mjs'
import { currentUser, logout } from '../auth'
import BrandMark from './BrandMark.vue'

const router = useRouter()
const route = useRoute()
const clockNow = ref(new Date())
const sidebarCollapsed = ref(false)
const showBackToTop = ref(false)
let clockTimer: number | undefined

const weekdays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']

function pad(value: number) {
  return String(value).padStart(2, '0')
}

const adminNav = [
  { path: '/admin/dashboard', label: '工作台', icon: LayoutDashboard },
  { path: '/admin/users', label: '用户管理', icon: Users },
  { path: '/admin/roles', label: '角色管理', icon: ShieldCheck },
  { path: '/admin/menus', label: '菜单管理', icon: FolderTree },
  { path: '/admin/notifications', label: '通知管理', icon: Bell },
  { path: '/admin/permissions', label: '权限管理', icon: KeyRound },
  { path: '/admin/data', label: '业务数据', icon: Database },
  { path: '/admin/logs', label: '审计日志', icon: ScrollText },
  { path: '/admin/settings', label: '系统配置', icon: Settings },
]
const pinnedTab = { path: '/admin/dashboard', title: '工作台' }
const openTabs = ref<Array<{ path: string; title: string }>>([{ ...pinnedTab }])
const adminNavByPath = new Map(adminNav.map((item) => [item.path, item.label]))

const userInitial = computed(() => currentUser.value?.display_name?.slice(0, 1) || 'A')
const currentNavLabel = computed(() => String(route.meta.title || '管理端'))
const headerClock = computed(() => {
  const value = clockNow.value
  const calendarDate = `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}`
  const time = `${pad(value.getHours())}:${pad(value.getMinutes())}:${pad(value.getSeconds())}`
  return {
    date: `${calendarDate} ${weekdays[value.getDay()]}`,
    time,
    datetime: `${calendarDate}T${time}`,
  }
})

onMounted(() => {
  clockTimer = window.setInterval(() => {
    clockNow.value = new Date()
  }, 1000)
  window.addEventListener('scroll', handleScroll, { passive: true })
})

onBeforeUnmount(() => {
  if (clockTimer !== undefined) window.clearInterval(clockTimer)
  window.removeEventListener('scroll', handleScroll)
})

watch(
  () => route.fullPath,
  () => {
    if (!route.path.startsWith('/admin')) return
    const title = String(route.meta.title || adminNavByPath.get(route.path) || '管理端')
    const existing = openTabs.value.find((tab) => tab.path === route.path)
    if (!existing) openTabs.value.push({ path: route.path, title })
  },
  { immediate: true },
)

function openTab(path: string) {
  if (path !== route.path) router.push(path)
}

function closeTab(path: string) {
  if (path === pinnedTab.path) return
  const index = openTabs.value.findIndex((tab) => tab.path === path)
  if (index < 0) return
  const wasActive = route.path === path
  openTabs.value.splice(index, 1)
  if (wasActive) {
    const nextPath = openTabs.value[Math.max(0, index - 1)]?.path || pinnedTab.path
    router.push(nextPath)
  }
}

function tabIcon(path: string) {
  return adminNav.find((item) => item.path === path)?.icon
}

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

function handleScroll() {
  showBackToTop.value = window.scrollY > 480
}

function scrollToTop() {
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  window.scrollTo({ top: 0, behavior: reducedMotion ? 'auto' : 'smooth' })
}

async function handleLogout() {
  await logout()
  router.replace('/login')
}
</script>

<template>
  <div class="app-shell" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
    <header class="app-header">
      <div class="app-header-brand">
        <BrandMark :size="34" />
        <span class="app-header-copy">
          <strong>SLD 管理端</strong>
          <span>{{ currentNavLabel }}</span>
        </span>
        <button
          class="sidebar-toggle"
          type="button"
          :aria-expanded="!sidebarCollapsed"
          :aria-label="sidebarCollapsed ? '展开左侧导航' : '收起左侧导航'"
          :title="sidebarCollapsed ? '展开左侧导航' : '收起左侧导航'"
          @click="toggleSidebar"
        >
          <PanelLeftOpen v-if="sidebarCollapsed" :size="20" aria-hidden="true" />
          <PanelLeftClose v-else :size="20" aria-hidden="true" />
        </button>
      </div>
      <div class="app-header-actions">
        <time class="app-header-clock" :datetime="headerClock.datetime" :title="`当前时间：${headerClock.date} ${headerClock.time}`">
          <Clock3 :size="17" aria-hidden="true" />
          <span class="clock-date">{{ headerClock.date }}</span>
          <strong>{{ headerClock.time }}</strong>
        </time>
        <div class="app-header-account">
          <span class="account-avatar">{{ userInitial }}</span>
          <span class="account-name">{{ currentUser?.display_name }}</span>
          <button class="sign-out-button" @click="handleLogout">
            <LogOut :size="16" :stroke-width="2" aria-hidden="true" />
            退出登录
          </button>
        </div>
      </div>
    </header>

    <div class="app-body">
      <aside class="app-sidebar">
        <nav>
          <div class="nav-group-label">管理端</div>
          <RouterLink v-for="item in adminNav" :key="item.path" :to="item.path">
            <component :is="item.icon" class="nav-icon" :size="19" :stroke-width="2" aria-hidden="true" />
            <span>{{ item.label }}</span>
          </RouterLink>
        </nav>
      </aside>

      <div class="app-workspace">
        <div v-if="openTabs.length" class="workspace-tabs" aria-label="已打开页面">
          <span
            v-for="tab in openTabs"
            :key="tab.path"
            class="workspace-tab"
            :class="{ 'is-active': route.path === tab.path }"
          >
            <button type="button" class="workspace-tab-open" @click="openTab(tab.path)">
              <component :is="tabIcon(tab.path)" :size="16" aria-hidden="true" />
              <span>{{ tab.title }}</span>
            </button>
            <button
              v-if="tab.path !== pinnedTab.path"
              type="button"
              class="workspace-tab-close"
              :aria-label="`关闭${tab.title}`"
              @click.stop="closeTab(tab.path)"
            >
              <X :size="14" :stroke-width="2" aria-hidden="true" />
            </button>
          </span>
        </div>
        <main>
          <RouterView />
        </main>
        <button v-show="showBackToTop" class="back-to-top" type="button" aria-label="回到顶部" @click="scrollToTop">
          <ArrowUp :size="18" :stroke-width="2" aria-hidden="true" />
          顶部
        </button>
      </div>
    </div>
  </div>
</template>
