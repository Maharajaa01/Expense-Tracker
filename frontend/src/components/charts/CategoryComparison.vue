<script setup lang="ts">
/** This period vs the previous one, per category. Current in violet, previous in de-emphasis gray; values always shown. */
import { computed } from 'vue'
import CategoryIcon from '@/components/ui/CategoryIcon.vue'
import Money from '@/components/ui/Money.vue'
import type { CategoryComparisonRow } from '@/types/finance'
import ChartPanel from './ChartPanel.vue'

const props = defineProps<{ rows: CategoryComparisonRow[]; currentLabel: string; previousLabel: string }>()
const max = computed(() => Math.max(1, ...props.rows.flatMap((r) => [r.current, r.previous])))
const w = (v: number) => `${Math.max((v / max.value) * 100, v > 0 ? 1.5 : 0)}%`
function changeText(r: CategoryComparisonRow) {
  if (r.change === null) return r.current > 0 ? 'new' : ''
  if (Math.abs(r.change) < 0.5) return 'same'
  return `${r.change > 0 ? '+' : '−'}${Math.abs(Math.round(r.change))}%`
}
</script>

<template>
  <ChartPanel title="Compared with before" :subtitle="`Spending by category, ${currentLabel} vs ${previousLabel}`">
    <template #legend>
      <ul class="mb-3 flex gap-4 text-[13px] text-ink-muted" aria-label="Legend">
        <li class="flex items-center gap-1.5"><span class="h-2 w-4 rounded-full bg-accent" />{{ currentLabel }}</li>
        <li class="flex items-center gap-1.5"><span class="h-2 w-4 rounded-full bg-ink-faint/60" />{{ previousLabel }}</li>
      </ul>
    </template>
    <p v-if="!rows.length" class="py-12 text-center text-sm text-ink-muted">No spending in either period.</p>
    <ul v-else class="space-y-3.5">
      <li v-for="r in rows" :key="r.category" class="grid grid-cols-[2rem_1fr] items-start gap-3">
        <CategoryIcon :icon="r.icon" :color="r.color" size="sm" />
        <div class="min-w-0">
          <div class="flex items-baseline justify-between gap-2">
            <span class="truncate text-sm font-medium text-ink">{{ r.category_name }}</span>
            <span class="shrink-0 text-xs tabular text-ink-muted">{{ changeText(r) }}</span>
          </div>
          <div class="mt-1 flex items-center gap-2">
            <div class="h-2 flex-1 rounded-full bg-ink/[0.05]"><div class="h-2 rounded-full bg-accent" :style="{ width: w(r.current) }" /></div>
            <Money :value="r.current" size="sm" hide-fraction class="w-20 text-right text-xs text-ink" />
          </div>
          <div class="mt-1 flex items-center gap-2">
            <div class="h-2 flex-1 rounded-full bg-ink/[0.05]"><div class="h-2 rounded-full bg-ink-faint/60" :style="{ width: w(r.previous) }" /></div>
            <Money :value="r.previous" size="sm" hide-fraction tone="muted" class="w-20 text-right text-xs" />
          </div>
        </div>
      </li>
    </ul>
  </ChartPanel>
</template>
