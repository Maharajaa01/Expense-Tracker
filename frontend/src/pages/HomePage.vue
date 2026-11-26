<script setup lang="ts">
import { computed, defineAsyncComponent, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import InstallAppButton from '@/components/InstallAppButton.vue'
import NotificationBell from '@/components/NotificationBell.vue'
import ResponsiveSheet from '@/components/ui/ResponsiveSheet.vue'
import CategoriseSheet from '@/features/transactions/CategoriseSheet.vue'
import AppCard from '@/components/ui/AppCard.vue'
import CategoryIcon from '@/components/ui/CategoryIcon.vue'
import InsightList from '@/components/ui/InsightList.vue'
import ProgressBar from '@/components/ui/ProgressBar.vue'
import ProgressRing from '@/components/ui/ProgressRing.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import Money from '@/components/ui/Money.vue'
import StatTile from '@/components/ui/StatTile.vue'
import TransactionRow from '@/components/ui/TransactionRow.vue'
import PeriodPicker, { type PeriodValue } from '@/features/dashboard/PeriodPicker.vue'
import { readThrough } from '@/offline/cache'
import { usePendingRows } from '@/offline/pendingRows'
import { ApiError } from '@/services/api'
import { boot } from '@/services/boot'
import { dashboardApi } from '@/services/finance'
import { useFinanceStore } from '@/stores/finance'
import { useUiStore } from '@/stores/ui'
import type { DashboardSummary } from '@/types/finance'
import { dayLabel, fromISO, greeting, longDate } from '@/utils/date'

// Charts (and ECharts) load in their own chunk so balances and totals paint first.
const CategoryBreakdown = defineAsyncComponent(() => import('@/components/charts/CategoryBreakdown.vue'))
const IncomeExpenseChart = defineAsyncComponent(() => import('@/components/charts/IncomeExpenseChart.vue'))
const SpendingTrendChart = defineAsyncComponent(() => import('@/components/charts/SpendingTrendChart.vue'))

const finance = useFinanceStore()
const ui = useUiStore()
const router = useRouter()
const name = computed(() => boot.data?.user.first_name ?? '')

const period = ref<PeriodValue>({ preset: 'this_month' })
const savedAt = ref<number | null>(null)
const categoriseOpen = ref(false)
const pendingRows = usePendingRows()
const data = ref<DashboardSummary | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
let seq = 0

async function load() {
  if (period.value.preset === 'custom' && (!period.value.from || !period.value.to)) return
  const id = ++seq
  loading.value = true
  error.value = null
  try {
    const fetcher = () => dashboardApi.summary(period.value.preset, period.value.from, period.value.to)
    const res = period.value.preset === 'this_month' ? await readThrough('dashboard:this_month', fetcher) : { data: await fetcher(), savedAt: null }
    if (id === seq) {
      data.value = res.data
      savedAt.value = res.savedAt
    }
  } catch (e) {
    if (id === seq) error.value = e instanceof ApiError ? e.message : 'Could not load your dashboard.'
  } finally {
    if (id === seq) loading.value = false
  }
}
watch(period, load, { deep: true, immediate: true })
watch(() => finance.dataVersion, load)

const periodName = computed(() => {
  const p = data.value?.period
  if (!p) return ''
  const fmt = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short' })
  return {
    today: 'today', this_week: 'this week', this_month: 'this month', last_month: 'last month',
    this_quarter: 'this quarter', this_year: 'this year',
  }[p.preset as string] ?? `${fmt.format(fromISO(p.from_date))} to ${fmt.format(fromISO(p.to_date))}`
})
const prevName = computed(() => ({ today: 'yesterday', this_week: 'last week', this_month: 'last month', last_month: 'the month before' })[period.value.preset as string] ?? 'the previous period')

/** "18% more than last month" (expense: more is worse, so it reads in plain words, not colour). */
function changeHint(pct: number | null | undefined): string | null {
  if (pct === null || pct === undefined) return null
  if (Math.abs(pct) < 0.5) return `Same as ${prevName.value}`
  return `${Math.abs(Math.round(pct))}% ${pct > 0 ? 'more' : 'less'} than ${prevName.value}`
}
const savingsHint = computed(() => {
  const r = data.value?.totals.savings_rate
  return r === null || r === undefined ? 'No income recorded' : `${r}% of income saved`
})
const recent = computed(() => (data.value ? [...pendingRows.created.value, ...pendingRows.overlay(data.value.recent)].slice(0, 5) : []))
const hasAnyData = computed(() => !!data.value && recent.value.length > 0)
</script>

<template>
  <div>
    <header class="mb-5 flex items-center justify-between gap-3">
      <div>
        <p class="text-sm text-ink-muted">{{ longDate() }}</p>
        <h1 class="text-2xl font-bold tracking-tight text-ink sm:text-[28px]">{{ greeting() }}, {{ name }}</h1>
      </div>
      <div class="flex items-center gap-2">
        <NotificationBell />
        <RouterLink :to="{ name: 'profile' }" class="lg:hidden" aria-label="Profile">
          <img v-if="boot.data?.user.image" :src="boot.data.user.image" alt="" class="size-10 rounded-full object-cover" />
          <span v-else class="inline-flex size-10 items-center justify-center rounded-full bg-accent-soft font-semibold text-accent">{{ name[0]?.toUpperCase() }}</span>
        </RouterLink>
      </div>
    </header>

    <InstallAppButton variant="banner" class="mb-4 lg:hidden" />

    <ErrorState v-if="error && !data" :message="error" :retrying="loading" @retry="load" />

    <template v-else>

      <button
        v-if="data?.to_categorise"
        type="button"
        class="mb-4 flex w-full items-center gap-3 rounded-card bg-warn-soft/70 p-4 text-left ring-1 ring-warn/20 hover:bg-warn-soft"
        @click="categoriseOpen = true"
      >
        <span class="inline-flex size-10 shrink-0 items-center justify-center rounded-full bg-card text-warn"><AppIcon name="tags" class="size-5" /></span>
        <span class="min-w-0 flex-1">
          <span class="block font-semibold text-ink">{{ data.to_categorise }} {{ data.to_categorise === 1 ? 'payment' : 'payments' }} to categorise</span>
          <span class="block text-[13px] text-ink-muted">Added from your bank alerts. Balances are already updated.</span>
        </span>
        <AppIcon name="chevron-right" class="size-5 text-ink-muted" />
      </button>

      <PeriodPicker v-model="period" class="mb-4" />
      <p v-if="savedAt" class="-mt-1 mb-4 text-sm text-ink-muted">
        Showing figures saved at {{ new Date(savedAt).toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' }) }}. Entries made offline are included once they sync.
      </p>

      <div class="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-3">
        <StatTile label="Income" :value="data?.totals.income ?? 0" icon="arrow-down-left" tone="income" :loading="loading && !data" :hint="changeHint(data?.change.income) ?? `Received ${periodName}`" />
        <StatTile label="Spent" :value="data?.totals.expense ?? 0" icon="arrow-up-right" tone="expense" :loading="loading && !data" :hint="changeHint(data?.change.expense) ?? `Spent ${periodName}`" />
        <StatTile label="Saved" :value="data?.totals.savings ?? 0" icon="piggy-bank" tone="savings" :loading="loading && !data" :hint="savingsHint" class="col-span-2 lg:col-span-1" />
      </div>

      <div v-if="data && !hasAnyData" class="mb-4 rounded-card bg-card ring-1 ring-line/60">
        <EmptyState icon="sparkles" title="Start by adding a transaction" message="Your balance, spending and charts fill in as you record income and expenses.">
          <button type="button" class="h-10 rounded-full bg-brand-solid px-5 text-sm font-semibold text-white" @click="ui.openQuickAdd()">Add transaction</button>
        </EmptyState>
      </div>

      <div v-if="data && (data.insights.length || data.budget_alerts.length || data.upcoming.length || data.goals.length)" class="mb-4 grid gap-4 lg:grid-cols-2 [&>*]:min-w-0">
        <InsightList v-if="data.insights.length" :insights="data.insights" />

        <section v-if="data.budget_alerts.length" class="rounded-card bg-card p-4 ring-1 ring-line/60 sm:p-5" aria-label="Budget alerts">
          <header class="mb-3 flex items-center justify-between">
            <h2 class="text-[15px] font-semibold text-ink">Budget alerts</h2>
            <RouterLink :to="{ name: 'budgets' }" class="text-sm font-medium text-brand-ink hover:underline">Budgets</RouterLink>
          </header>
          <ul class="space-y-3.5">
            <li v-for="b in data.budget_alerts" :key="b.name" class="grid grid-cols-[2rem_1fr] items-start gap-3">
              <CategoryIcon :icon="b.icon" :color="b.color" size="sm" />
              <div class="min-w-0">
                <div class="flex justify-between gap-2 text-sm">
                  <span class="truncate font-medium text-ink">{{ b.budget_name }}</span>
                  <span v-if="b.progress!.remaining < 0" class="font-semibold text-expense"><Money :value="-b.progress!.remaining" size="sm" hide-fraction /> over</span>
                  <span v-else class="text-ink-muted"><Money :value="b.progress!.remaining" size="sm" hide-fraction /> left</span>
                </div>
                <ProgressBar :percent="b.progress!.percent" :label="`${b.budget_name} ${Math.round(b.progress!.percent ?? 0)}% used`" height="sm" class="mt-1.5" />
              </div>
            </li>
          </ul>
        </section>

        <section v-if="data.upcoming.length" class="rounded-card bg-card p-4 ring-1 ring-line/60 sm:p-5" aria-label="Upcoming payments">
          <header class="mb-2 flex items-center justify-between">
            <h2 class="text-[15px] font-semibold text-ink">Due in the next 7 days</h2>
            <RouterLink :to="{ name: 'recurring' }" class="text-sm font-medium text-brand-ink hover:underline">All</RouterLink>
          </header>
          <ul class="divide-y divide-line/60">
            <li v-for="u in data.upcoming" :key="`${u.recurring}-${u.date}`" class="flex items-center gap-3 py-2.5 text-sm">
              <span class="w-20 shrink-0 font-medium" :class="u.overdue ? 'text-expense' : 'text-ink-muted'">{{ u.overdue ? 'Overdue' : dayLabel(u.date) }}</span>
              <span class="min-w-0 flex-1 truncate text-ink">{{ u.title }}</span>
              <Money :value="u.transaction_type === 'Income' ? u.amount : -u.amount" :sign="u.transaction_type === 'Income' ? 'always' : 'auto'" :tone="u.transaction_type === 'Income' ? 'income' : 'inherit'" size="sm" class="text-ink" />
            </li>
          </ul>
        </section>

        <section v-if="data.goals.length" class="rounded-card bg-card p-4 ring-1 ring-line/60 sm:p-5" aria-label="Savings goals">
          <header class="mb-3 flex items-center justify-between">
            <h2 class="text-[15px] font-semibold text-ink">Savings goals</h2>
            <RouterLink :to="{ name: 'goals' }" class="text-sm font-medium text-brand-ink hover:underline">All</RouterLink>
          </header>
          <ul class="space-y-3">
            <li v-for="g in data.goals" :key="g.name" class="flex items-center gap-3">
              <ProgressRing :percent="g.percent" tone="savings" :size="48" :stroke="5" :label="`${g.goal_name} ${Math.round(g.percent ?? 0)}% saved`">
                <span class="text-[11px] font-semibold tabular text-ink">{{ Math.round(g.percent ?? 0) }}%</span>
              </ProgressRing>
              <span class="min-w-0 flex-1">
                <span class="block truncate text-sm font-medium text-ink">{{ g.goal_name }}</span>
                <span class="block text-[13px] text-ink-muted"><Money :value="g.current_amount" size="sm" hide-fraction /> of <Money :value="g.target_amount" size="sm" hide-fraction /></span>
              </span>
            </li>
          </ul>
        </section>
      </div>

      <div v-if="data" class="grid items-start gap-4 lg:grid-cols-5 [&>*]:min-w-0" :class="{ 'opacity-60 transition-opacity': loading }">
        <SpendingTrendChart class="lg:col-span-3" :points="data.trend.points" :grain="data.trend.granularity" :subtitle="`Spent ${periodName}`" />
        <CategoryBreakdown
          class="lg:col-span-2"
          :categories="data.categories"
          :total="data.totals.expense"
          :subtitle="periodName ? `Where your money went ${periodName}` : undefined"
          @select="(c) => router.push({ name: 'transactions', query: { category: c, range: 'custom', from_date: data!.period.from_date, to_date: data!.period.to_date } })"
        />
        <IncomeExpenseChart class="lg:col-span-3" :points="data.monthly" grain="month" subtitle="Last 6 months" />

        <section class="rounded-card bg-card p-4 ring-1 ring-line/60 sm:p-5 lg:col-span-2">
          <header class="mb-2 flex items-center justify-between">
            <h2 class="text-[15px] font-semibold text-ink">Recent transactions</h2>
            <RouterLink :to="{ name: 'transactions' }" class="text-sm font-medium text-brand-ink hover:underline">See all</RouterLink>
          </header>
          <p v-if="!recent.length" class="py-8 text-center text-sm text-ink-muted">Nothing recorded yet.</p>
          <TransactionRow v-for="t in recent" :key="t.name" :txn="t" show-date @select="router.push({ name: 'transactions' })" />
        </section>
      </div>
    </template>

    <ResponsiveSheet v-model:open="categoriseOpen" title="To categorise" size="lg">
      <CategoriseSheet v-if="categoriseOpen" @done="categoriseOpen = false" />
    </ResponsiveSheet>
  </div>
</template>
