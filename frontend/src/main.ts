import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'

import App from './App.vue'
import AdminLayout from './components/AdminLayout.vue'
import { authReady, currentUser, restoreSession } from './auth'
import './styles.css'

const routes = [
  { path: '/', redirect: '/admin/dashboard' },
  { path: '/login', component: () => import('./views/LoginView.vue'), meta: { public: true } },
  {
    path: '/admin',
    component: AdminLayout,
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/admin/dashboard' },
      { path: 'dashboard', component: () => import('./views/DashboardView.vue'), meta: { requiresAuth: true, title: '工作台' } },
      { path: 'users', component: () => import('./views/UsersView.vue'), meta: { requiresAuth: true, title: '用户管理' } },
      { path: 'roles', component: () => import('./views/RolesView.vue'), meta: { requiresAuth: true, title: '角色管理' } },
      { path: 'menus', component: () => import('./views/MenusView.vue'), meta: { requiresAuth: true, title: '菜单管理' } },
      { path: 'notifications', component: () => import('./views/NotificationsView.vue'), meta: { requiresAuth: true, title: '通知管理' } },
      { path: 'data', component: () => import('./views/DataView.vue'), meta: { requiresAuth: true, title: '业务数据' } },
      { path: 'logs', component: () => import('./views/LogsView.vue'), meta: { requiresAuth: true, title: '审计日志' } },
      { path: 'settings', component: () => import('./views/SettingsView.vue'), meta: { requiresAuth: true, title: '系统配置' } },
      { path: 'entry-fields', component: () => import('./views/EntryFieldConfigView.vue'), meta: { requiresAuth: true, title: '录单字段配置' } },
      { path: 'field-conversions', component: () => import('./views/FieldConversionConfigView.vue'), meta: { requiresAuth: true, title: '字段转换配置' } },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  if (!authReady.value) await restoreSession()
  if (to.meta.requiresAuth && !currentUser.value) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.meta.public && currentUser.value) {
    return '/admin/dashboard'
  }
  return true
})

function isStaleRouteChunkError(error: unknown): boolean {
  return error instanceof Error
    && /Failed to fetch dynamically imported module/i.test(error.message)
}

const ROUTE_RELOAD_PARAM = '_route_reload'
const ROUTE_RELOAD_MARKER = 'fruit-ana-admin:route-chunk-reload'

router.onError((error, to) => {
  console.error('[router] navigation failed', error)
  if (!isStaleRouteChunkError(error)) return
  if (window.sessionStorage.getItem(ROUTE_RELOAD_MARKER)) return
  window.sessionStorage.setItem(ROUTE_RELOAD_MARKER, '1')
  const url = new URL(to.fullPath, window.location.origin)
  url.searchParams.set(ROUTE_RELOAD_PARAM, String(Date.now()))
  window.location.replace(url.toString())
})

router.afterEach(() => {
  window.sessionStorage.removeItem(ROUTE_RELOAD_MARKER)
})

createApp(App).use(router).mount('#app')
