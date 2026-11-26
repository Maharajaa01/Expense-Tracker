<script setup lang="ts">
/** Budget use as meters: fill tone carries severity, the label always states it. */
import ProgressBar from '@/components/ui/ProgressBar.vue'
import CategoryIcon from '@/components/ui/CategoryIcon.vue'
import Money from '@/components/ui/Money.vue'
import type { Budget } from '@/types/finance'
import ChartPanel from './ChartPanel.vue'

defineProps<{ budgets: Budget[] }>()
</script>

<template>
  <ChartPanel title="Budget use" subtitle="How much of each budget is spent">
    <div v-if="!budgets.length" class="py-10 text-center text-sm text-ink-muted">
      No budgets in this period. <RouterLink :to="{ name: 'budgets' }" class="font-medium text-brand-ink hover:underline">Create one</RouterLink>
    </div>
    <ul v-else class="space-y-4">
      <li v-for="b in budgets" :key="b.name" class="grid grid-cols-[2rem_1fr] items-start gap-3">
        <CategoryIcon :icon="b.icon" :color="b.color" size="sm" />
        <div class="min-w-0">
          <div class="flex items-baseline justify-between gap-2 text-sm">
            <span class="truncate font-medium text-ink">{{ b.budget_name }}</span>
            <span class="shrink-0 tabular" :class="b.progress!.level === 'over' || b.progress!.level === '100' ? 'font-semibold text-expense' : 'text-ink-muted'">
              {{ b.progress!.percent === null ? '—' : `${Math.round(b.progress!.percent)}%` }}{{ b.progress!.level === 'over' ? ' over' : '' }}
            </span>
          </div>
          <ProgressBar :percent="b.progress!.percent" :label="`${b.budget_name} ${Math.round(b.progress!.percent ?? 0)}% used`" class="mt-1.5" height="sm" />
          <p class="mt-1 text-xs text-ink-muted"><Money :value="b.progress!.spent" size="sm" hide-fraction /> of <Money :value="b.progress!.available" size="sm" hide-fraction /></p>
        </div>
      </li>
    </ul>
  </ChartPanel>
</template>
