<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import ArrowUp from '@lucide/vue/dist/esm/icons/arrow-up.mjs'
import ArrowLeftRight from '@lucide/vue/dist/esm/icons/arrow-left-right.mjs'
import Bell from '@lucide/vue/dist/esm/icons/bell.mjs'
import BookOpen from '@lucide/vue/dist/esm/icons/book-open.mjs'
import ClipboardPen from '@lucide/vue/dist/esm/icons/clipboard-pen.mjs'
import Clock3 from '@lucide/vue/dist/esm/icons/clock-3.mjs'
import Database from '@lucide/vue/dist/esm/icons/database.mjs'
import Eye from '@lucide/vue/dist/esm/icons/eye.mjs'
import EyeOff from '@lucide/vue/dist/esm/icons/eye-off.mjs'
import FolderTree from '@lucide/vue/dist/esm/icons/folder-tree.mjs'
import KeyRound from '@lucide/vue/dist/esm/icons/key-round.mjs'
import LayoutDashboard from '@lucide/vue/dist/esm/icons/layout-dashboard.mjs'
import LogOut from '@lucide/vue/dist/esm/icons/log-out.mjs'
import MessageCircle from '@lucide/vue/dist/esm/icons/message-circle.mjs'
import PanelLeftClose from '@lucide/vue/dist/esm/icons/panel-left-close.mjs'
import PanelLeftOpen from '@lucide/vue/dist/esm/icons/panel-left-open.mjs'
import PanelRightClose from '@lucide/vue/dist/esm/icons/panel-right-close.mjs'
import RefreshCw from '@lucide/vue/dist/esm/icons/refresh-cw.mjs'
import ScrollText from '@lucide/vue/dist/esm/icons/scroll-text.mjs'
import Settings from '@lucide/vue/dist/esm/icons/settings.mjs'
import ShieldCheck from '@lucide/vue/dist/esm/icons/shield-check.mjs'
import SquareX from '@lucide/vue/dist/esm/icons/square-x.mjs'
import Users from '@lucide/vue/dist/esm/icons/users.mjs'
import X from '@lucide/vue/dist/esm/icons/x.mjs'
import { currentUser, logout } from '../auth'
import { post } from '../api/client'
import { notify } from '../feedback'
import BrandMark from './BrandMark.vue'

const router = useRouter()
const route = useRoute()
const clockNow = ref(new Date())
const sidebarCollapsed = ref(false)
const showBackToTop = ref(false)
const viewKey = ref(0)
const contextMenu = ref<{ x: number; y: number; path: string } | null>(null)
const backToTopThreshold = 240
let clockTimer: number | undefined

const showPasswordModal = ref(false)
const passwordSaving = ref(false)
const oldPasswordVisible = ref(false)
const newPasswordVisible = ref(false)
const confirmationVisible = ref(false)
const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmation: '',
})

function openChangePassword() {
  passwordForm.oldPassword = ''
  passwordForm.newPassword = ''
  passwordForm.confirmation = ''
  showPasswordModal.value = true
}

async function submitChangePassword() {
  if (!passwordForm.oldPassword || !passwordForm.newPassword || !passwordForm.confirmation) {
    notify('请完整填写旧密码和新密码', 'error')
    return
  }
  if (passwordForm.newPassword.length < 8) {
    notify('新密码至少需要 8 位', 'error')
    return
  }
  if (passwordForm.newPassword !== passwordForm.confirmation) {
    notify('两次输入的新密码不一致', 'error')
    return
  }
  passwordSaving.value = true
  try {
    await post('/api/admin/auth/change-password', {
      old_password: passwordForm.oldPassword,
      new_password: passwordForm.newPassword,
      confirmation: passwordForm.confirmation,
    })
    notify('密码已修改')
    showPasswordModal.value = false
  } catch (err) {
    notify(err instanceof Error ? err.message : '修改密码失败', 'error')
  } finally {
    passwordSaving.value = false
  }
}

const weekdays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']

function pad(value: number) {
  return String(value).padStart(2, '0')
}

const adminNav = computed(() => [
  { path: '/admin/dashboard', label: '工作台', icon: LayoutDashboard },
  { path: '/admin/users', label: '用户管理', icon: Users },
  { path: '/admin/roles', label: '角色管理', icon: ShieldCheck },
  { path: '/admin/menus', label: '菜单管理', icon: FolderTree },
  { path: '/admin/notifications', label: '通知管理', icon: Bell },
  { path: '/admin/data', label: '业务数据', icon: Database },
  { path: '/admin/logs', label: '审计日志', icon: ScrollText },
  { path: '/admin/settings', label: '系统配置', icon: Settings },
  { path: '/admin/entry-fields', label: '录单字段配置', icon: ClipboardPen },
  { path: '/admin/field-conversions', label: '字段转换配置', icon: ArrowLeftRight },
])
const pinnedTab = { path: '/admin/dashboard', title: '工作台' }
const openTabs = ref<Array<{ path: string; title: string }>>([{ ...pinnedTab }])
const adminNavByPath = computed(() => new Map(adminNav.value.map((item) => [item.path, item.label])))

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
const contextMenuStyle = computed(() => {
  if (!contextMenu.value) return {}
  const menuWidth = 168
  const menuHeight = 180
  const left = Math.min(Math.max(8, contextMenu.value.x), window.innerWidth - menuWidth - 12)
  const top = Math.min(Math.max(8, contextMenu.value.y), window.innerHeight - menuHeight - 12)
  return { left: `${left}px`, top: `${top}px` }
})

onMounted(() => {
  clockTimer = window.setInterval(() => {
    clockNow.value = new Date()
  }, 1000)
  window.addEventListener('scroll', handleScroll, { passive: true })
  document.addEventListener('scroll', handleScroll, { passive: true, capture: true })
  document.addEventListener('click', closeContextMenu)
  document.addEventListener('keydown', handleGlobalKeydown)
  handleScroll()
})

onBeforeUnmount(() => {
  if (clockTimer !== undefined) window.clearInterval(clockTimer)
  window.removeEventListener('scroll', handleScroll)
  document.removeEventListener('scroll', handleScroll, { capture: true })
  document.removeEventListener('click', closeContextMenu)
  document.removeEventListener('keydown', handleGlobalKeydown)
})

watch(
  () => route.fullPath,
  () => {
    if (!route.path.startsWith('/admin')) return
    const title = String(route.meta.title || adminNavByPath.value.get(route.path) || '管理端')
    const existing = openTabs.value.find((tab) => tab.path === route.path)
    if (!existing) openTabs.value.push({ path: route.path, title })
  },
  { immediate: true },
)

function openTab(path: string) {
  if (path !== route.path) router.push(path)
}

function closeTab(path: string) {
  closeContextMenu()
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

function closeOtherTabs(path: string) {
  openTabs.value = openTabs.value.filter((tab) => tab.path === pinnedTab.path || tab.path === path)
  if (route.path !== path) void router.push(path)
  closeContextMenu()
}

function closeAllTabs() {
  openTabs.value = [{ ...pinnedTab }]
  if (route.path !== pinnedTab.path) void router.push(pinnedTab.path)
  closeContextMenu()
}

function refreshTab(path: string) {
  if (route.path !== path) {
    void router.push(path).then(() => {
      viewKey.value += 1
    })
  } else {
    viewKey.value += 1
  }
  closeContextMenu()
}

function tabIcon(path: string) {
  return adminNav.value.find((item) => item.path === path)?.icon
}

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

function readScrollTop(target?: EventTarget | null) {
  if (target instanceof HTMLElement && target.scrollTop > 0) return target.scrollTop
  return window.scrollY || document.documentElement.scrollTop || document.body.scrollTop
}

function handleScroll(event?: Event) {
  showBackToTop.value = readScrollTop(event?.target) > backToTopThreshold
}

function openTabContextMenu(event: MouseEvent, path: string) {
  contextMenu.value = { x: event.clientX, y: event.clientY, path }
}

function closeContextMenu() {
  contextMenu.value = null
}

function handleGlobalKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') closeContextMenu()
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
          <button class="sign-out-button" @click="openChangePassword">
            <KeyRound :size="16" :stroke-width="2" aria-hidden="true" />
            修改密码
          </button>
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
            @contextmenu.prevent="openTabContextMenu($event, tab.path)"
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
          <RouterView :key="viewKey" />
        </main>
        <footer class="app-footer">
          <span class="app-footer-copy">SLD-水果市场销售分析系统©2026</span>
          <nav class="app-footer-actions" aria-label="系统服务">
            <button type="button"><BookOpen :size="16" :stroke-width="2" aria-hidden="true" />使用手册</button>
            <button type="button" class="wechat-qr-button">
              <MessageCircle :size="16" :stroke-width="2" aria-hidden="true" />微信公众号
              <img class="wechat-qr-popover" src="/gzh.jpg" alt="SLD-水果市场销售分析系统 微信公众号二维码" />
            </button>
          </nav>
        </footer>
        <div
          v-if="contextMenu"
          class="tab-context-menu"
          :style="contextMenuStyle"
          role="menu"
          @click.stop
          @contextmenu.prevent
        >
          <button type="button" role="menuitem" @click="refreshTab(contextMenu.path)">
            <RefreshCw :size="15" :stroke-width="2" aria-hidden="true" />
            刷新当前
          </button>
          <button type="button" role="menuitem" :disabled="contextMenu.path === pinnedTab.path" @click="closeTab(contextMenu.path)">
            <X :size="15" :stroke-width="2" aria-hidden="true" />
            关闭当前
          </button>
          <button type="button" role="menuitem" @click="closeOtherTabs(contextMenu.path)">
            <PanelRightClose :size="15" :stroke-width="2" aria-hidden="true" />
            关闭其他
          </button>
          <button type="button" role="menuitem" class="danger-text" @click="closeAllTabs">
            <SquareX :size="15" :stroke-width="2" aria-hidden="true" />
            关闭全部
          </button>
        </div>
        <button v-show="showBackToTop" class="back-to-top" type="button" aria-label="回到顶部" @click="scrollToTop">
          <ArrowUp :size="18" :stroke-width="2" aria-hidden="true" />
          顶部
        </button>
      </div>
    </div>
  </div>

  <div v-if="showPasswordModal" class="drawer-mask" @click.self="showPasswordModal = false">
    <div class="drawer" role="dialog" aria-modal="true" aria-label="修改密码">
      <div class="drawer-header">
        <div class="drawer-title">修改管理端密码</div>
        <button class="link-button" @click="showPasswordModal = false">关闭</button>
      </div>
      <div class="drawer-body">
        <div class="field">
          <label>旧密码</label>
          <div class="password-input">
            <input v-model="passwordForm.oldPassword" :type="oldPasswordVisible ? 'text' : 'password'" class="input" autocomplete="current-password" />
            <button type="button" class="password-toggle-button" :aria-label="oldPasswordVisible ? '隐藏旧密码' : '显示旧密码'" @click="oldPasswordVisible = !oldPasswordVisible">
              <EyeOff v-if="oldPasswordVisible" :size="17" :stroke-width="2" aria-hidden="true" />
              <Eye v-else :size="17" :stroke-width="2" aria-hidden="true" />
            </button>
          </div>
        </div>
        <div class="field">
          <label>新密码</label>
          <div class="password-input">
            <input v-model="passwordForm.newPassword" :type="newPasswordVisible ? 'text' : 'password'" class="input" autocomplete="new-password" minlength="8" />
            <button type="button" class="password-toggle-button" :aria-label="newPasswordVisible ? '隐藏新密码' : '显示新密码'" @click="newPasswordVisible = !newPasswordVisible">
              <EyeOff v-if="newPasswordVisible" :size="17" :stroke-width="2" aria-hidden="true" />
              <Eye v-else :size="17" :stroke-width="2" aria-hidden="true" />
            </button>
          </div>
        </div>
        <div class="field">
          <label>再次输入新密码</label>
          <div class="password-input">
            <input v-model="passwordForm.confirmation" :type="confirmationVisible ? 'text' : 'password'" class="input" autocomplete="new-password" minlength="8" />
            <button type="button" class="password-toggle-button" :aria-label="confirmationVisible ? '隐藏确认密码' : '显示确认密码'" @click="confirmationVisible = !confirmationVisible">
              <EyeOff v-if="confirmationVisible" :size="17" :stroke-width="2" aria-hidden="true" />
              <Eye v-else :size="17" :stroke-width="2" aria-hidden="true" />
            </button>
          </div>
        </div>
      </div>
      <div class="drawer-actions">
        <button class="secondary-button" @click="showPasswordModal = false">取消</button>
        <button class="primary-button" :disabled="passwordSaving" @click="submitChangePassword">
          {{ passwordSaving ? '提交中...' : '确认修改' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.password-input {
  position: relative;
}

.password-input .input {
  padding-right: 2.7rem;
}

.password-toggle-button {
  position: absolute;
  top: 50%;
  right: .65rem;
  transform: translateY(-50%);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
}

.password-toggle-button:hover {
  background: var(--surface-hover, #f4f4f5);
  color: var(--ink);
}
</style>
