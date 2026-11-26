<script setup lang="ts" generic="T extends string">
/** Radio group styled as segments. Arrow keys move the selection. */
import AppIcon from './AppIcon.vue'

export interface SegmentOption<V> {
  value: V
  label: string
  icon?: string
  /** Selected colour. */
  tone?: 'brand' | 'income' | 'expense' | 'accent'
}

const props = defineProps<{ options: SegmentOption<T>[]; label: string; size?: 'sm' | 'md' }>()
const model = defineModel<T>({ required: true })

function onKey(e: KeyboardEvent, i: number) {
  const n = props.options.length
  const step = e.key === 'ArrowRight' || e.key === 'ArrowDown' ? 1 : e.key === 'ArrowLeft' || e.key === 'ArrowUp' ? -1 : 0
  if (!step) return
  e.preventDefault()
  const next = props.options[(i + step + n) % n]
  model.value = next.value
  const group = (e.currentTarget as HTMLElement).parentElement
  ;(group?.children[(i + step + n) % n] as HTMLElement | undefined)?.focus()
}

const toneClass = {
  brand: 'bg-brand-solid text-white',
  income: 'bg-income-solid text-white',
  expense: 'bg-expense-solid text-white',
  accent: 'bg-accent-solid text-white',
}
</script>

<template>
  <div role="radiogroup" :aria-label="label" class="flex rounded-full bg-ink/[0.06] p-1">
    <button
      v-for="(opt, i) in options"
      :key="opt.value"
      type="button"
      role="radio"
      :aria-checked="model === opt.value"
      :tabindex="model === opt.value ? 0 : -1"
      class="flex flex-1 items-center justify-center gap-1.5 rounded-full font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
      :class="[
        size === 'sm' ? 'h-8 px-2 text-[13px]' : 'h-10 px-4 text-sm',
        model === opt.value ? toneClass[opt.tone ?? 'brand'] + ' shadow-sm' : 'text-ink-muted hover:text-ink',
      ]"
      @click="model = opt.value"
      @keydown="onKey($event, i)"
    >
      <AppIcon v-if="opt.icon" :name="opt.icon" class="size-4" />
      {{ opt.label }}
    </button>
  </div>
</template>
