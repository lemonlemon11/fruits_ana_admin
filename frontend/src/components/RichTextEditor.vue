<script setup lang="ts">
import '@vueup/vue-quill/dist/vue-quill.snow.css'
import { QuillEditor } from '@vueup/vue-quill'
import { notify } from '../feedback'

const props = defineProps<{ modelValue: string }>()
const emit = defineEmits<{ (event: 'update:modelValue', value: string): void }>()

type QuillEditorExposed = InstanceType<typeof QuillEditor>
type QuillInstance = ReturnType<QuillEditorExposed['getQuill']>

let quill: QuillInstance | null = null

const toolbar = [
  [{ header: [1, 2, 3, false] }],
  ['bold', 'italic', 'underline', 'strike'],
  [{ color: [] }, { background: [] }],
  [{ list: 'ordered' }, { list: 'bullet' }],
  ['blockquote', 'link', 'image'],
  ['clean'],
]

function insertLocalImage() {
  if (!quill) return
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'image/*'
  input.addEventListener('change', () => {
    const file = input.files?.[0]
    if (!file) return
    if (file.size > 2 * 1024 * 1024) {
      notify('图片不能超过 2MB，请压缩后再上传', 'error')
      return
    }
    const reader = new FileReader()
    reader.addEventListener('load', () => {
      if (!quill || typeof reader.result !== 'string') return
      const range = quill.getSelection(true)
      const index = range?.index ?? quill.getLength()
      quill.insertEmbed(index, 'image', reader.result, 'user')
      quill.setSelection(index + 1, 0, 'silent')
    })
    reader.readAsDataURL(file)
  })
  input.click()
}

const editorOptions = {
  modules: {
    toolbar: {
      container: toolbar,
      handlers: {
        image: insertLocalImage,
      },
    },
  },
}

function handleReady(instance: QuillInstance) {
  quill = instance
}
</script>

<template>
  <div class="rich-editor">
    <QuillEditor
      :content="modelValue"
      contentType="html"
      theme="snow"
      :options="editorOptions"
      placeholder="请输入通知内容"
      @update:content="emit('update:modelValue', $event)"
      @ready="handleReady"
    />
  </div>
</template>

<style scoped>
.rich-editor {
  overflow: hidden;
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-md);
  background: var(--surface);
}

.rich-editor :deep(.ql-toolbar.ql-snow) {
  padding: .47rem .59rem;
  border: 0;
  border-bottom: 1px solid var(--line);
  background: var(--surface-soft);
}

.rich-editor :deep(.ql-container.ql-snow) {
  min-height: 13.5rem;
  border: 0;
  color: var(--ink);
  font-family: inherit;
  font-size: .96rem;
}

.rich-editor :deep(.ql-editor) {
  min-height: 13.5rem;
  padding: .82rem .88rem;
  line-height: 1.75;
}

.rich-editor :deep(.ql-editor.ql-blank::before) {
  color: var(--muted);
  font-style: normal;
  left: .88rem;
  right: .88rem;
}

.rich-editor :deep(.ql-snow .ql-toolbar button:hover),
.rich-editor :deep(.ql-snow .ql-toolbar button:focus),
.rich-editor :deep(.ql-snow .ql-toolbar button.ql-active) {
  color: var(--primary-dark);
}

.rich-editor :deep(.ql-snow .ql-toolbar button:hover .ql-fill),
.rich-editor :deep(.ql-snow .ql-toolbar button:focus .ql-fill),
.rich-editor :deep(.ql-snow .ql-toolbar button.ql-active .ql-fill) {
  fill: var(--primary);
}

.rich-editor :deep(.ql-snow .ql-toolbar button:hover .ql-stroke),
.rich-editor :deep(.ql-snow .ql-toolbar button:focus .ql-stroke),
.rich-editor :deep(.ql-snow .ql-toolbar button.ql-active .ql-stroke) {
  stroke: var(--primary);
}

.rich-editor :deep(.ql-snow.ql-toolbar .ql-picker-label:hover),
.rich-editor :deep(.ql-snow.ql-toolbar .ql-picker-label.ql-active) {
  color: var(--primary-dark);
}

.rich-editor :deep(.ql-editor img) {
  max-width: 100%;
  height: auto;
  border-radius: var(--radius-sm);
}
</style>
