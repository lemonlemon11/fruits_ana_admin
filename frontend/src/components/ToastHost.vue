<script setup lang="ts">
import { toastState } from '../feedback'
</script>

<template>
  <div class="toast-host" aria-live="polite">
    <div v-for="item in toastState.items" :key="item.id" class="toast" :class="item.kind">
      {{ item.message }}
    </div>
  </div>
</template>
