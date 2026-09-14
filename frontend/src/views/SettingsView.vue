<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { get, patch } from '../api/client'
import { notify } from '../feedback'
import { hasPermission } from '../auth'

type SettingItem = { key: string; value: string | null; description: string | null }

const items = ref<SettingItem[]>([])
const editingKey = ref<string | null>(null)
const editValue = ref('')
const error = ref('')
const saving = ref(false)

async function load() {
  error.value = ''
  try {
    const data = await get<{ items: SettingItem[] }>('/api/admin/settings')
    items.value = data.items
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载失败'
  }
}

function openEdit(item: SettingItem) {
  editingKey.value = item.key
  editValue.value = item.value || ''
}

async function save() {
  if (!editingKey.value) return
  saving.value = true
  try {
    await patch(`/api/admin/settings/${editingKey.value}`, { value: editValue.value })
    notify('配置已保存')
    editingKey.value = null
    await load()
  } catch (err) {
    notify(err instanceof Error ? err.message : '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <section class="page-stack">
    <div class="page-header">
      <div class="page-heading">
        <h1>系统配置</h1>
        <p class="page-description">管理登录、会话与安全策略</p>
      </div>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <div class="card table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th>配置项</th>
            <th>值</th>
            <th>说明</th>
            <th v-if="hasPermission('admin:config:update')">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.key">
            <td><code>{{ item.key }}</code></td>
            <td>
              <span v-if="editingKey !== item.key">{{ item.value || '—' }}</span>
              <input v-else v-model="editValue" class="input" />
            </td>
            <td>{{ item.description || '—' }}</td>
            <td v-if="hasPermission('admin:config:update')">
              <button v-if="editingKey !== item.key" class="link-button" @click="openEdit(item)">编辑</button>
              <template v-else>
                <button class="primary-button" :disabled="saving" @click="save">{{ saving ? '保存中...' : '保存' }}</button>
                <button class="secondary-button" :disabled="saving" @click="editingKey = null">取消</button>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
