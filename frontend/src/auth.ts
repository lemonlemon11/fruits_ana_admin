import { computed, ref } from 'vue'
import { get, post } from './api/client'
import type { AuthUser } from './types'

export const currentUser = ref<AuthUser | null>(null)
export const authReady = ref(false)

export const permissions = computed(() => new Set(currentUser.value?.permissions || []))

export function hasPermission(code: string) {
  return permissions.value.has(code)
}

export async function restoreSession() {
  try {
    currentUser.value = await get<{ user: AuthUser }>('/api/admin/auth/me').then((r) => r.user)
  } catch {
    currentUser.value = null
  } finally {
    authReady.value = true
  }
}

export async function login(displayName: string, password: string, rememberMe: boolean) {
  const response = await post<{ user: AuthUser }>('/api/admin/auth/login', {
    display_name: displayName,
    password,
    remember_me: rememberMe,
  })
  currentUser.value = response.user
}

export async function logout() {
  await post('/api/admin/auth/logout')
  currentUser.value = null
}
