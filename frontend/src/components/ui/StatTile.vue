<script setup lang="ts">
import AppIcon from './AppIcon.vue'
import Money from './Money.vue'

withDefaults(
  defineProps<{
    label: string
    value: number | null
    icon: string
    tone: 'income' | 'expense' | 'savings' | 'accent'
    /** Short context line, e.g. "32% of income". */
    hint?: string | null
    loading?: boolean
  }>(),
  { hint: null, loading: false },
)
</script>

<template>
  <div class="flex flex-col items-start gap-2 rounded-card bg-card p-3.5 ring-1 ring-line/60 sm:flex-row sm:gap-3 sm:p-4">
    <span
      class="inline-flex size-9 shrink-0 items-center justify-center rounded-full"
      :class="{
        income: 'bg-income-soft text-income',
        expense: 'bg-expense-soft text-expense',
        savings: 'bg-savings-soft text-savings',
        accent: 'bg-accent-soft text-accent',
      }[tone]"
    >
      <AppIcon :name="icon" class="size-[18px]" />
    </span>
    <div class="min-w-0">
      <p class="text-[13px] text-ink-muted">{{ label }}</p>
      <div v-if="loading" class="mt-1.5 h-5 w-24 animate-pulse rounded bg-ink/10" />
      <Money v-else-if="value !== null" :value="value" size="lg" class="mt-0.5 block text-ink" />
      <p v-else class="mt-0.5 text-xl font-semibold text-ink-faint">—</p>
      <p v-if="hint && !loading" class="mt-0.5 text-xs text-ink-muted">{{ hint }}</p>
    </div>
  </div>
</template>
