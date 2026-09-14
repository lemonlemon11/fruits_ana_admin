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
      { path: 'dashboard', component: () => import('./views/DashboardView.vue'), meta: { requiresAuth: true, permission: 'admin:dashboard:view', title: '工作台' } },
      { path: 'users', component: () => import('./views/UsersView.vue'), meta: { requiresAuth: true, permission: 'admin:user:view', title: '用户管理' } },
      { path: 'roles', component: () => import('./views/RolesView.vue'), meta: { requiresAuth: true, permission: 'admin:role:view', title: '角色管理' } },
      { path: 'menus', component: () => import('./views/MenusView.vue'), meta: { requiresAuth: true, permission: 'admin:menu:view', title: '菜单管理' } },
      { path: 'notifications', component: () => import('./views/NotificationsView.vue'), meta: { requiresAuth: true, permission: 'admin:notification:view', title: '通知管理' } },
      { path: 'permissions', component: () => import('./views/PermissionsView.vue'), meta: { requiresAuth: true, permission: 'admin:permission:view', title: '权限管理' } },
      { path: 'data', component: () => import('./views/DataView.vue'), meta: { requiresAuth: true, permission: 'admin:data:view', title: '业务数据' } },
      { path: 'logs', component: () => import('./views/LogsView.vue'), meta: { requiresAuth: true, permission: 'admin:log:view', title: '审计日志' } },
      { path: 'settings', component: () => import('./views/SettingsView.vue'), meta: { requiresAuth: true, permission: 'admin:config:view', title: '系统配置' } },
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
  if (to.meta.permission && !currentUser.value?.permissions.includes(String(to.meta.permission))) {
    return '/admin/dashboard'
  }
  return true
})

createApp(App).use(router).mount('#app')
