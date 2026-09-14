<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

const props = defineProps<{ modelValue: string }>()
const emit = defineEmits<{ (event: 'update:modelValue', value: string): void }>()
const editor = ref<HTMLElement | null>(null)

onMounted(() => {
  if (editor.value && props.modelValue) editor.value.innerHTML = props.modelValue
})

watch(
  () => props.modelValue,
  (value) => {
    if (editor.value && value !== editor.value.innerHTML) editor.value.innerHTML = value
  },
)

function run(command: string, value?: string) {
  editor.value?.focus()
  document.execCommand(command, false, value)
  emitChange()
}

function emitChange() {
  if (editor.value) emit('update:modelValue', editor.value.innerHTML)
}
</script>

<template>
  <div class="rich-editor">
    <div class="rich-editor-toolbar" role="toolbar" aria-label="富文本工具栏">
      <button type="button" title="加粗" @mousedown.prevent="run('bold')">B</button>
      <button type="button" title="斜体" @mousedown.prevent="run('italic')">I</button>
      <button type="button" title="下划线" @mousedown.prevent="run('underline')">U</button>
      <span class="rich-editor-sep"></span>
      <button type="button" title="无序列表" @mousedown.prevent="run('insertUnorderedList')">• 列表</button>
      <button type="button" title="有序列表" @mousedown.prevent="run('insertOrderedList')">1. 列表</button>
      <span class="rich-editor-sep"></span>
      <button type="button" title="插入链接" @mousedown.prevent="run('createLink', prompt('请输入链接地址') || '')">链接</button>
      <button type="button" title="移除格式" @mousedown.prevent="run('removeFormat')">清除格式</button>
    </div>
    <div
      ref="editor"
      class="rich-editor-content"
      contenteditable="true"
      role="textbox"
      aria-multiline="true"
      @input="emitChange"
      @blur="emitChange"
    ></div>
  </div>
</template>

<style scoped>
.rich-editor {
  overflow: hidden;
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-md);
  background: var(--surface);
}
.rich-editor-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: .35rem;
  padding: .47rem;
  border-bottom: 1px solid var(--line);
  background: var(--surface-soft);
}
.rich-editor-toolbar button {
  min-height: 2.24rem;
  padding: 0 .59rem;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: var(--surface);
  color: var(--ink);
  font-size: .88rem;
  font-weight: 700;
}
.rich-editor-toolbar button:hover { border-color: var(--primary); color: var(--primary-dark); }
.rich-editor-sep {
  width: 1px;
  height: 1.35rem;
  align-self: center;
  background: var(--line);
}
.rich-editor-content {
  min-height: 9.41rem;
  padding: .82rem;
  outline: none;
  color: var(--ink);
  line-height: 1.7;
}
.rich-editor-content:empty::before {
  color: var(--muted);
  content: '请输入通知内容';
}
</style>
