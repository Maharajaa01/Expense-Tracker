<script setup lang="ts">
import { computed } from 'vue'
import { clampPercent, toneForUtilisation, type ProgressTone } from './progress'

const props = withDefaults(
  defineProps<{ percent: number | null; tone?: ProgressTone | 'auto'; label: string; height?: 'sm' | 'md' }>(),
  { tone: 'auto', height: 'md' },
)
const width = computed(() => clampPercent(props.percent))
const resolved = computed(() => (props.tone === 'auto' ? toneForUtilisation(props.percent ?? 0) : props.tone))
</script>

<template>
  <div
    role="progressbar"
    :aria-label="label"
    aria-valuemin="0"
    aria-valuemax="100"
    :aria-valuenow="Math.round(percent ?? 0)"
    class="w-full overflow-hidden rounded-full bg-ink/[0.07]"
    :class="height === 'sm' ? 'h-1.5' : 'h-2.5'"
  >
    <div
      class="h-full rounded-full transition-[width] duration-500 ease-out motion-reduce:transition-none"
      :class="{ brand: 'bg-brand', warn: 'bg-warn', expense: 'bg-expense', savings: 'bg-savings', accent: 'bg-accent' }[resolved]"
      :style="{ width: `${width}%` }"
    />
  </div>
</template>
