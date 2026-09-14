<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import Database from '@lucide/vue/dist/esm/icons/database.mjs'
import LogIn from '@lucide/vue/dist/esm/icons/log-in.mjs'
import ScrollText from '@lucide/vue/dist/esm/icons/scroll-text.mjs'
import ShieldCheck from '@lucide/vue/dist/esm/icons/shield-check.mjs'
import Users from '@lucide/vue/dist/esm/icons/users.mjs'
import { login } from '../auth'
import { ApiError } from '../api/client'
import BrandMark from '../components/BrandMark.vue'

const router = useRouter()
const displayName = ref('')
const password = ref('')
const rememberMe = ref(false)
const error = ref('')
const loading = ref(false)

const featureItems = [
  { label: '用户管理', icon: Users },
  { label: '角色权限', icon: ShieldCheck },
  { label: '业务数据', icon: Database },
  { label: '审计日志', icon: ScrollText },
]

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await login(displayName.value.trim(), password.value, rememberMe.value)
    router.replace('/admin/dashboard')
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="portal">
    <section class="portal-visual">
      <header class="portal-brand">
        <BrandMark :size="38" tone="inverse" />
        <span class="portal-brand-copy">
          <strong>SLD 水果市场销售分析</strong>
          <small>管理员控制台</small>
        </span>
      </header>

      <div class="portal-hero">
        <p class="portal-kicker">统一管理入口</p>
        <h1>把系统权限，<br />管得更清楚。</h1>
        <p class="portal-lede">集中管理用户、角色、菜单与权限，查看业务数据与审计日志。</p>
        <ul class="portal-features">
          <li v-for="item in featureItems" :key="item.label">
            <component :is="item.icon" :size="15" :stroke-width="2" aria-hidden="true" />
            {{ item.label }}
          </li>
        </ul>
      </div>

      <dl class="portal-facts">
        <div>
          <dt>权限模型</dt>
          <dd>RBAC</dd>
        </div>
        <div>
          <dt>菜单策略</dt>
          <dd>动态分配</dd>
        </div>
        <div>
          <dt>数据来源</dt>
          <dd>fruits_ana</dd>
        </div>
      </dl>
    </section>

    <section class="portal-panel">
      <div class="portal-panel-inner">
        <div class="portal-form-card">
          <form class="auth-form" @submit.prevent="submit">
            <header>
              <h2>登录管理端</h2>
              <p>请使用管理员分配的账号登录</p>
            </header>
            <div class="auth-field">
              <label for="login-username">用户名</label>
              <div class="auth-input">
                <input id="login-username" v-model="displayName" autocomplete="username" required />
              </div>
            </div>
            <div class="auth-field">
              <label for="login-password">密码</label>
              <div class="auth-input">
                <input id="login-password" v-model="password" type="password" autocomplete="current-password" required />
              </div>
            </div>
            <label class="auth-remember">
              <input v-model="rememberMe" type="checkbox" />
              30 天内免登录
            </label>
            <button class="primary-button auth-submit" :disabled="loading">
              <LogIn :size="17" :stroke-width="2" aria-hidden="true" />
              {{ loading ? '登录中...' : '登录' }}
            </button>
            <p v-if="error" class="form-message error">{{ error }}</p>
          </form>
        </div>
      </div>
    </section>
  </main>
</template>
