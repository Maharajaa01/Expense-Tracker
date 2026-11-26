<script setup lang="ts">
import { computed, defineAsyncComponent, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import ErrorState from '@/components/ui/ErrorState.vue'
import InsightList from '@/components/ui/InsightList.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SkeletonRows from '@/components/ui/SkeletonRows.vue'
import StatTile from '@/components/ui/StatTile.vue'
import PeriodPicker, { type PeriodValue } from '@/features/dashboard/PeriodPicker.vue'
import { ApiError } from '@/services/api'
import { analyticsApi } from '@/services/finance'
import { useFinanceStore } from '@/stores/finance'
import type { AnalyticsSummary, PeriodPreset } from '@/types/finance'
import { fromISO } from '@/utils/date'

const IncomeExpenseChart = defineAsyncComponent(() => import('@/components/charts/IncomeExpenseChart.vue'))
const SpendingTrendChart = defineAsyncComponent(() => import('@/components/charts/SpendingTrendChart.vue'))
const CategoryBreakdown = defineAsyncComponent(() => import('@/components/charts/CategoryBreakdown.vue'))
const MonthlySpendingChart = defineAsyncComponent(() => import('@/components/charts/MonthlySpendingChart.vue'))
const SavingsTrendChart = defineAsyncComponent(() => import('@/components/charts/SavingsTrendChart.vue'))
const CategoryComparison = defineAsyncComponent(() => import('@/components/charts/CategoryComparison.vue'))
const BudgetUtilization = defineAsyncComponent(() => import('@/components/charts/BudgetUtilization.vue'))

const finance = useFinanceStore()
const router = useRouter()
const presets: { value: PeriodPreset; label: string }[] = [
  { value: 'today', label: 'Today' }, { value: 'this_week', label: 'Week' }, { value: 'this_month', label: 'Month' },
  { value: 'this_quarter', label: 'Quarter' }, { value: 'this_year', label: 'Year' }, { value: 'custom', label: 'Custom' },
]
const period = ref<PeriodValue>({ preset: 'this_month' })
const data = ref<AnalyticsSummary | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
let seq = 0

async function load() {
  if (period.value.preset === 'custom' && (!period.value.from || !period.value.to)) return
  const id = ++seq
  loading.value = true
  error.value = null
  try {
    const res = await analyticsApi.summary(period.value.preset, period.value.from, period.value.to)
    if (id === seq) data.value = res
  } catch (e) {
    if (id === seq) error.value = e instanceof ApiError ? e.message : 'Could not load analytics.'
  } finally {
    if (id === seq) loading.value = false
  }
}
watch(period, load, { deep: true, immediate: true })
watch(() => finance.dataVersion, load)

const fmt = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short' })
const labels = computed(() => {
  const p = data.value?.period
  if (!p) return { current: '', previous: '' }
  const named: Record<string, [string, string]> = {
    today: ['Today', 'Yesterday'], this_week: ['This week', 'Last week'], this_month: ['This month', 'Last month'],
    this_quarter: ['This quarter', 'Last quarter'], this_year: ['This year', 'Last year'],
  }
  return named[p.preset]
    ? { current: named[p.preset][0], previous: named[p.preset][1] }
    : { current: `${fmt.format(fromISO(p.from_date))} to ${fmt.format(fromISO(p.to_date))}`, previous: 'the period before' }
})
function changeHint(pct: number | null | undefined) {
  if (pct === null || pct === undefined) return null
  if (Math.abs(pct) < 0.5) return `Same as ${labels.value.previous.toLowerCase()}`
  return `${Math.abs(Math.round(pct))}% ${pct > 0 ? 'more' : 'less'} than ${labels.value.previous.toLowerCase()}`
}
function openCategory(c: string) {
  const p = data.value!.period
  router.push({ name: 'transactions', query: { category: c, range: 'custom', from_date: p.from_date, to_date: p.to_date } })
}
</script>

<template>
  <div>
    <PageHeader title="Analytics" />
    <PeriodPicker v-model="period" :presets="presets" class="mb-4" />

    <ErrorState v-if="error && !data" :message="error" :retrying="loading" @retry="load" />
    <div v-else-if="!data" class="rounded-card bg-card px-3 ring-1 ring-line/60"><SkeletonRows :rows="5" /></div>

    <div v-else class="space-y-4" :class="{ 'opacity-60 transition-opacity': loading }">
      <div class="grid grid-cols-2 gap-3 lg:grid-cols-3">
        <StatTile label="Income" :value="data.totals.income" icon="arrow-down-left" tone="income" :hint="changeHint(data.change.income)" />
        <StatTile label="Spent" :value="data.totals.expense" icon="arrow-up-right" tone="expense" :hint="changeHint(data.change.expense)" />
        <StatTile label="Saved" :value="data.totals.savings" icon="piggy-bank" tone="savings" class="col-span-2 lg:col-span-1"
          :hint="data.totals.savings_rate === null ? 'No income in this period' : `${data.totals.savings_rate}% of income saved`" />
      </div>

      <InsightList :insights="data.insights" />
      <p v-if="!data.insights.length" class="rounded-card bg-card p-4 text-sm text-ink-muted ring-1 ring-line/60">
        Insights appear once there's enough income and spending in this period to compare.
      </p>

      <div class="grid gap-4 lg:grid-cols-2 [&>*]:min-w-0">
        <IncomeExpenseChart :points="data.trend.points" :grain="data.trend.granularity" :subtitle="labels.current" />
        <SpendingTrendChart v-if="data.daily" :points="data.daily" grain="day" :subtitle="labels.current" />
        <SpendingTrendChart v-else :points="data.trend.points" :grain="data.trend.granularity" :subtitle="labels.current" />
        <CategoryBreakdown :categories="data.categories" :total="data.totals.expense" :subtitle="labels.current" @select="openCategory" />
        <CategoryComparison :rows="data.comparison" :current-label="labels.current" :previous-label="labels.previous" />
        <MonthlySpendingChart :points="data.monthly" />
        <SavingsTrendChart :points="data.savings" />
        <BudgetUtilization :budgets="data.budgets" class="lg:col-span-2" />
      </div>
    </div>
  </div>
</template>
