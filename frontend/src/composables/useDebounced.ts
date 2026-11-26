import { ref, watch, type Ref } from 'vue'

/** A copy of `source` that updates `delay` ms after it stops changing. */
export function useDebounced<T>(source: Ref<T>, delay = 300): Ref<T> {
  const out = ref(source.value) as Ref<T>
  let timer: ReturnType<typeof setTimeout> | undefined
  watch(source, (v) => {
    clearTimeout(timer)
    timer = setTimeout(() => (out.value = v), delay)
  })
  return out
}
