import { onBeforeUnmount, ref } from 'vue'

/** Reactive `min-width: 1024px` (Tailwind `lg`). Desktop layout above it. */
export function useIsDesktop() {
  const mq = window.matchMedia('(min-width: 1024px)')
  const isDesktop = ref(mq.matches)
  const update = (e: MediaQueryListEvent) => (isDesktop.value = e.matches)
  mq.addEventListener('change', update)
  onBeforeUnmount(() => mq.removeEventListener('change', update))
  return isDesktop
}
