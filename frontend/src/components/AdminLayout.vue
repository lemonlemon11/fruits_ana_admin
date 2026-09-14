<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import Bell from '@lucide/vue/dist/esm/icons/bell.mjs'
import Clock3 from '@lucide/vue/dist/esm/icons/clock-3.mjs'
import Database from '@lucide/vue/dist/esm/icons/database.mjs'
import FolderTree from '@lucide/vue/dist/esm/icons/folder-tree.mjs'
import KeyRound from '@lucide/vue/dist/esm/icons/key-round.mjs'
import LayoutDashboard from '@lucide/vue/dist/esm/icons/layout-dashboard.mjs'
import LogOut from '@lucide/vue/dist/esm/icons/log-out.mjs'
import ScrollText from '@lucide/vue/dist/esm/icons/scroll-text.mjs'
import Settings from '@lucide/vue/dist/esm/icons/settings.mjs'
import ShieldCheck from '@lucide/vue/dist/esm/icons/shield-check.mjs'
import Users from '@lucide/vue/dist/esm/icons/users.mjs'
import { currentUser, logout } from '../auth'
import BrandMark from './BrandMark.vue'

const router = useRouter()
const route = useRoute()
const clockNow = ref(new Date())
let clockTimer: number | undefined

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

const userInitial = computed(() => currentUser.value?.display_name?.slice(0, 1) || 'A')
const currentNavLabel = computed(() => String(route.meta.title || '管理端'))
const headerClock = computed(() => ({
  date: clockNow.value.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit', weekday: 'short' }),
  time: clockNow.value.toLocaleTimeString('zh-CN', { hour12: false }),
}))

onMounted(() => {
  clockTimer = window.setInterval(() => {
    clockNow.value = new Date()
  }, 1000)
})

onBeforeUnmount(() => {
  if (clockTimer !== undefined) window.clearInterval(clockTimer)
})

async function handleLogout() {
  await logout()
  router.replace('/login')
}
</script>

<template>
  <div class="app-shell">
    <header class="app-header">
      <div class="app-header-brand">
        <BrandMark :size="34" />
        <span class="app-header-copy">
          <strong>SLD 管理端</strong>
          <span>{{ currentNavLabel }}</span>
        </span>
      </div>
      <div class="app-header-actions">
        <time class="app-header-clock" :datetime="clockNow.toISOString()" :title="`当前时间：${headerClock.date} ${headerClock.time}`">
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
        <main>
          <RouterView />
        </main>
      </div>
    </div>
  </div>
</template>
