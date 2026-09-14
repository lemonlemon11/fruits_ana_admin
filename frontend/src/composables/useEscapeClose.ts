import { onBeforeUnmount, onMounted } from 'vue'

export function useEscapeClose(isOpen: () => boolean, close: () => void) {
  function handleKeydown(event: KeyboardEvent) {
    if (event.key !== 'Escape' || !isOpen()) return
    event.preventDefault()
    event.stopPropagation()
    close()
  }

  onMounted(() => document.addEventListener('keydown', handleKeydown))
  onBeforeUnmount(() => document.removeEventListener('keydown', handleKeydown))
}
