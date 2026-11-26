<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import CategoryIcon from '@/components/ui/CategoryIcon.vue'
import Money from '@/components/ui/Money.vue'
import ProgressBar from '@/components/ui/ProgressBar.vue'
import type { Budget } from '@/types/finance'

const props = defineProps<{ budget: Budget }>()
defineEmits<{ select: [b: Budget] }>()
const p = computed(() => props.budget.progress)
const status = computed(() => {
  const l = p.value?.level
  if (l === 'over') return { text: 'Over budget', cls: 'bg-expense-soft text-expense', icon: 'triangle-alert' }
  if (l === '100') return { text: 'Used up', cls: 'bg-expense-soft text-expense', icon: 'circle-alert' }
  if (l === '80') return { text: '80% used', cls: 'bg-warn-soft text-warn', icon: 'circle-alert' }
  return null
})
</script>

<template>
  <button
    type="button"
    class="w-full rounded-card bg-card p-4 text-left ring-1 ring-line/60 transition-shadow hover:shadow-card focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand"
    :class="{ 'opacity-60': !budget.is_active }"
    @click="$emit('select', budget)"
  >
    <div class="flex items-center gap-3">
      <CategoryIcon :icon="budget.icon" :color="budget.color" />
      <div class="min-w-0 flex-1">
        <p class="truncate font-semibold text-ink">{{ budget.budget_name }}</p>
        <p class="text-[13px] text-ink-muted">
          {{ budget.category ? (budget.period_type === 'Monthly' ? 'Monthly' : 'Custom period') : 'All spending' }}<template v-if="!budget.is_active">, paused</template>
        </p>
      </div>
      <span v-if="status" class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold" :class="status.cls">
        <AppIcon :name="status.icon" class="size-3.5" /> {{ status.text }}
      </span>
    </div>

    <template v-if="p">
      <div class="mt-4 flex items-baseline justify-between gap-2">
        <span v-if="p.remaining >= 0" class="text-ink"><Money :value="p.remaining" size="lg" /> <span class="text-sm text-ink-muted">left</span></span>
        <span v-else class="text-expense"><Money :value="-p.remaining" size="lg" /> <span class="text-sm">over</span></span>
        <span class="text-sm tabular text-ink-muted">{{ p.percent === null ? '' : `${Math.round(p.percent)}%` }}</span>
      </div>
      <ProgressBar :percent="p.percent" :label="`${budget.budget_name}: ${Math.round(p.percent ?? 0)}% used`" class="mt-2" />
      <p class="mt-2 text-[13px] text-ink-muted">
        <Money :value="p.spent" size="sm" /> of <Money :value="p.available" size="sm" hide-fraction /> spent
        <template v-if="p.carried">, including <Money :value="p.carried" size="sm" hide-fraction /> carried over</template>
      </p>
    </template>
    <p v-else class="mt-3 text-[13px] text-ink-muted">Not running in this month.</p>
  </button>
</template>
