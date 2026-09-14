<script setup lang="ts">
import { confirmState, settleConfirm } from '../feedback'
import { useEscapeClose } from '../composables/useEscapeClose'

useEscapeClose(() => confirmState.open, () => settleConfirm(false))
</script>

<template>
  <div v-if="confirmState.open" class="modal-mask confirm-mask">
    <div class="modal confirm-dialog" role="dialog" aria-modal="true">
      <div class="modal-header">
        <div class="modal-title">{{ confirmState.title }}</div>
        <button class="link-button" @click="settleConfirm(false)">关闭</button>
      </div>
      <p class="confirm-message">{{ confirmState.message }}</p>
      <div class="modal-actions">
        <button class="secondary-button" @click="settleConfirm(false)">取消</button>
        <button :class="confirmState.danger ? 'danger-button' : 'primary-button'" @click="settleConfirm(true)">
          {{ confirmState.confirmText }}
        </button>
      </div>
    </div>
  </div>
</template>
