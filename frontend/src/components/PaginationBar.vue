<script setup lang="ts">
import { computed } from 'vue'
import ChevronLeft from '@lucide/vue/dist/esm/icons/chevron-left.mjs'
import ChevronRight from '@lucide/vue/dist/esm/icons/chevron-right.mjs'
import ChevronsLeft from '@lucide/vue/dist/esm/icons/chevrons-left.mjs'
import ChevronsRight from '@lucide/vue/dist/esm/icons/chevrons-right.mjs'

const props = withDefaults(defineProps<{
  page: number
  pageSize: number
  total: number
  pageSizeOptions?: number[]
}>(), {
  pageSizeOptions: () => [10, 20, 50, 100],
})

const emit = defineEmits<{
  (event: 'update:page', value: number): void
  (event: 'update:pageSize', value: number): void
  (event: 'change'): void
}>()

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / Math.max(1, props.pageSize))))
const pageItems = computed<Array<number | 'ellipsis'>>(() => {
  const total = totalPages.value
  const current = props.page
  if (total <= 7) return Array.from({ length: total }, (_, index) => index + 1)

  const items: Array<number | 'ellipsis'> = [1]
  if (current > 3) items.push('ellipsis')
  const start = Math.max(2, current - 1)
  const end = Math.min(total - 1, current + 1)
  for (let page = start; page <= end; page += 1) items.push(page)
  if (current < total - 2) items.push('ellipsis')
  items.push(total)
  return items
})

function goToPage(page: number) {
  if (page < 1 || page > totalPages.value || page === props.page) return
  emit('update:page', page)
  emit('change')
}

function handlePageSizeChange(event: Event) {
  const value = Number((event.target as HTMLSelectElement).value)
  if (!Number.isFinite(value) || value <= 0 || value === props.pageSize) return
  emit('update:pageSize', value)
  emit('update:page', 1)
  emit('change')
}
</script>

<template>
  <div class="pagination-bar">
    <span class="pagination-total">共 {{ total }} 条</span>
    <label class="pagination-size">
      每页
      <select :value="pageSize" @change="handlePageSizeChange">
        <option v-for="size in pageSizeOptions" :key="size" :value="size">{{ size }}</option>
      </select>
      条
    </label>
    <div class="pagination-pages" role="navigation" aria-label="分页导航">
      <button type="button" class="pagination-page" :disabled="page <= 1" aria-label="首页" @click="goToPage(1)">
        <ChevronsLeft :size="16" :stroke-width="2" aria-hidden="true" />
      </button>
      <button type="button" class="pagination-page" :disabled="page <= 1" aria-label="上一页" @click="goToPage(page - 1)">
        <ChevronLeft :size="16" :stroke-width="2" aria-hidden="true" />
      </button>
      <template v-for="(item, index) in pageItems" :key="`${item}-${index}`">
        <span v-if="item === 'ellipsis'" class="pagination-ellipsis">…</span>
        <button
          v-else
          type="button"
          class="pagination-page"
          :class="{ 'is-active': item === page }"
          :aria-current="item === page ? 'page' : undefined"
          @click="goToPage(item)"
        >
          {{ item }}
        </button>
      </template>
      <button type="button" class="pagination-page" :disabled="page >= totalPages" aria-label="下一页" @click="goToPage(page + 1)">
        <ChevronRight :size="16" :stroke-width="2" aria-hidden="true" />
      </button>
      <button type="button" class="pagination-page" :disabled="page >= totalPages" aria-label="末页" @click="goToPage(totalPages)">
        <ChevronsRight :size="16" :stroke-width="2" aria-hidden="true" />
      </button>
    </div>
  </div>
</template>
