<script setup lang="ts">
import { computed } from 'vue'
import { clampPercent, toneForUtilisation, type ProgressTone } from './progress'

const props = withDefaults(
  defineProps<{ percent: number | null; size?: number; stroke?: number; tone?: ProgressTone | 'auto'; label: string }>(),
  { size: 72, stroke: 8, tone: 'auto' },
)
const r = computed(() => (props.size - props.stroke) / 2)
const c = computed(() => 2 * Math.PI * r.value)
const offset = computed(() => c.value * (1 - clampPercent(props.percent) / 100))
const resolved = computed(() => (props.tone === 'auto' ? toneForUtilisation(props.percent ?? 0) : props.tone))
</script>

<template>
  <div
    class="relative inline-flex shrink-0 items-center justify-center"
    :style="{ width: `${size}px`, height: `${size}px` }"
    role="progressbar"
    :aria-label="label"
    aria-valuemin="0"
    aria-valuemax="100"
    :aria-valuenow="Math.round(percent ?? 0)"
  >
    <svg :width="size" :height="size" class="-rotate-90" aria-hidden="true">
      <circle :cx="size / 2" :cy="size / 2" :r="r" fill="none" :stroke-width="stroke" class="stroke-ink/[0.08]" />
      <circle
        :cx="size / 2"
        :cy="size / 2"
        :r="r"
        fill="none"
        :stroke-width="stroke"
        stroke-linecap="round"
        :stroke-dasharray="c"
        :stroke-dashoffset="offset"
        class="transition-[stroke-dashoffset] duration-700 ease-out motion-reduce:transition-none"
        :class="{ brand: 'stroke-brand', warn: 'stroke-warn', expense: 'stroke-expense', savings: 'stroke-savings', accent: 'stroke-accent' }[resolved]"
      />
    </svg>
    <div class="absolute inset-0 flex items-center justify-center">
      <slot>
        <span class="text-sm font-semibold tabular text-ink">{{ percent == null ? '—' : `${Math.round(percent)}%` }}</span>
      </slot>
    </div>
  </div>
</template>
