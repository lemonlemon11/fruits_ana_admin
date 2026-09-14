import { reactive } from 'vue'

export type ToastKind = 'success' | 'error' | 'info'

export interface ToastItem {
  id: number
  message: string
  kind: ToastKind
}

interface ConfirmState {
  open: boolean
  title: string
  message: string
  confirmText: string
  danger: boolean
  resolve: ((value: boolean) => void) | null
}

export const toastState = reactive<{ items: ToastItem[] }>({ items: [] })
export const confirmState = reactive<ConfirmState>({
  open: false,
  title: '确认操作',
  message: '',
  confirmText: '确认',
  danger: false,
  resolve: null,
})

let toastId = 0

export function notify(message: string, kind: ToastKind = 'success') {
  const id = ++toastId
  toastState.items.push({ id, message, kind })
  window.setTimeout(() => {
    const index = toastState.items.findIndex((item) => item.id === id)
    if (index >= 0) toastState.items.splice(index, 1)
  }, 3400)
}

export function confirmAction(message: string, options: {
  title?: string
  confirmText?: string
  danger?: boolean
} = {}) {
  confirmState.title = options.title || '确认操作'
  confirmState.message = message
  confirmState.confirmText = options.confirmText || '确认'
  confirmState.danger = options.danger ?? true
  confirmState.open = true
  return new Promise<boolean>((resolve) => {
    confirmState.resolve = resolve
  })
}

export function settleConfirm(value: boolean) {
  confirmState.open = false
  confirmState.resolve?.(value)
  confirmState.resolve = null
}
