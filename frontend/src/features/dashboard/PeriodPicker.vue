<script setup lang="ts">
import { ref, watch } from 'vue'
import type { PeriodPreset } from '@/types/finance'

export interface PeriodValue {
  preset: PeriodPreset
  from?: string
  to?: string
}

const props = defineProps<{ presets?: { value: PeriodPreset; label: string }[] }>()
const model = defineModel<PeriodValue>({ required: true })
const presets = props.presets ?? [
  { value: 'today', label: 'Today' },
  { value: 'this_week', label: 'This week' },
  { value: 'this_month', label: 'This month' },
  { value: 'last_month', label: 'Last month' },
  { value: 'custom', label: 'Custom' },
]
const from = ref(model.value.from ?? '')
const to = ref(model.value.to ?? '')

function choose(p: PeriodPreset) {
  if (p !== 'custom') model.value = { preset: p }
  else model.value = { preset: 'custom', from: from.value, to: to.value }
}
watch([from, to], () => {
  if (model.value.preset === 'custom' && from.value && to.value && to.value >= from.value)
    model.value = { preset: 'custom', from: from.value, to: to.value }
})
</script>

<template>
  <div>
    <div class="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 sm:mx-0 sm:px-0" role="radiogroup" aria-label="Period">
      <button
        v-for="p in presets"
        :key="p.value"
        type="button"
        role="radio"
        :aria-checked="model.preset === p.value"
        class="h-9 shrink-0 rounded-full px-4 text-sm font-medium ring-1 transition-colors"
        :class="model.preset === p.value ? 'bg-ink text-canvas ring-ink' : 'bg-card text-ink-muted ring-line hover:text-ink'"
        @click="choose(p.value)"
      >
        {{ p.label }}
      </button>
    </div>
    <div v-if="model.preset === 'custom'" class="mt-3 flex flex-wrap items-end gap-3">
      <label class="text-sm">
        <span class="mb-1 block font-medium text-ink">From</span>
        <input v-model="from" type="date" class="h-10 rounded-[10px] border-0 bg-card px-3 text-ink ring-1 ring-line focus:ring-2 focus:ring-brand" />
      </label>
      <label class="text-sm">
        <span class="mb-1 block font-medium text-ink">To</span>
        <input v-model="to" type="date" :min="from" class="h-10 rounded-[10px] border-0 bg-card px-3 text-ink ring-1 ring-line focus:ring-2 focus:ring-brand" />
      </label>
      <p v-if="!from || !to" class="pb-2 text-sm text-ink-muted">Choose both dates.</p>
    </div>
  </div>
</template>
