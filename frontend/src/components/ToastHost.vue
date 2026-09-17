<script setup lang="ts">
import CircleCheck from '@lucide/vue/dist/esm/icons/circle-check.mjs'
import Info from '@lucide/vue/dist/esm/icons/info.mjs'
import TriangleAlert from '@lucide/vue/dist/esm/icons/triangle-alert.mjs'
import { toastState, type ToastKind } from '../feedback'

const TOAST_ICONS = {
  success: CircleCheck,
  error: TriangleAlert,
  info: Info,
} satisfies Record<ToastKind, unknown>
</script>

<template>
  <div class="toast-host" aria-live="polite">
    <TransitionGroup name="toast">
      <div v-for="item in toastState.items" :key="item.id" class="toast" :class="item.kind" role="status">
        <component :is="TOAST_ICONS[item.kind]" class="toast-icon" :size="17" :stroke-width="2" aria-hidden="true" />
        <span class="toast-text">{{ item.message }}</span>
      </div>
    </TransitionGroup>
  </div>
</template>
