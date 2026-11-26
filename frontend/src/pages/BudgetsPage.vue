<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { dialog, toast } from 'frappe-ui'
import AppCard from '@/components/ui/AppCard.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import Money from '@/components/ui/Money.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import ProgressBar from '@/components/ui/ProgressBar.vue'
import ProgressRing from '@/components/ui/ProgressRing.vue'
import ResponsiveSheet from '@/components/ui/ResponsiveSheet.vue'
import SkeletonRows from '@/components/ui/SkeletonRows.vue'
import BudgetCard from '@/features/budgets/BudgetCard.vue'
import BudgetForm from '@/features/budgets/BudgetForm.vue'
import { readThrough } from '@/offline/cache'
import { ApiError } from '@/services/api'
import { budgetsApi } from '@/services/finance'
import { useFinanceStore } from '@/stores/finance'
import type { Budget, BudgetProgress } from '@/types/finance'
import { fromISO, toISO } from '@/utils/date'

const finance = useFinanceStore()
onMounted(() => finance.load())

const now = new Date()
const month = ref(new Date(now.getFullYear(), now.getMonth(), 1))
const isCurrentMonth = computed(() => month.value.getFullYear() === now.getFullYear() && month.value.getMonth() === now.getMonth())
const monthLabel = computed(() => new Intl.DateTimeFormat('en-IN', { month: 'long', year: 'numeric' }).format(month.value))
function shift(n: number) {
  month.value = new Date(month.value.getFullYear(), month.value.getMonth() + n, 1)
}

const budgets = ref<Budget[]>([])
const savedAt = ref<number | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
let seq = 0
async function load() {
  const id = ++seq
  loading.value = true
  error.value = null
  try {
    const fetcher = () => budgetsApi.list(toISO(month.value), true)
    const res = isCurrentMonth.value ? await readThrough('budgets:current', fetcher) : { data: await fetcher(), savedAt: null }
    if (id === seq) {
      budgets.value = res.data
      savedAt.value = res.savedAt
    }
  } catch (e) {
    if (id === seq) error.value = e instanceof ApiError ? e.message : 'Could not load budgets.'
  } finally {
    if (id === seq) loading.value = false
  }
}
watch(month, load, { immediate: true })
watch(() => finance.dataVersion, load)

const overall = computed(() => budgets.value.find((b) => !b.category && b.is_active && b.progress))
const active = computed(() => budgets.value.filter((b) => b.is_active && b !== overall.value))
const paused = computed(() => budgets.value.filter((b) => !b.is_active))

// Detail sheet
const selected = ref<Budget | null>(null)
const detailOpen = computed({ get: () => !!selected.value, set: (v) => !v && (selected.value = null) })
const history = ref<(BudgetProgress & { month: string })[]>([])
watch(selected, async (b) => {
  history.value = []
  if (b && b.period_type === 'Monthly') {
    try {
      history.value = (await budgetsApi.history(b.name, 6)).history
    } catch {
      /* history is supplementary; the sheet still works */
    }
  }
})
const monthShort = (iso: string) => new Intl.DateTimeFormat('en-IN', { month: 'short', year: '2-digit' }).format(fromISO(iso))

const formOpen = ref(false)
const editing = ref<Budget | null>(null)
function openCreate() {
  editing.value = null
  formOpen.value = true
}
function openEdit(b: Budget) {
  selected.value = null
  editing.value = b
  formOpen.value = true
}
async function toggleActive(b: Budget) {
  selected.value = null
  try {
    await budgetsApi.update(b.name, { is_active: b.is_active ? 0 : 1 })
    toast.success(b.is_active ? 'Budget paused' : 'Budget resumed')
    finance.dataVersion++
  } catch (e) {
    toast.error(e instanceof ApiError ? e.message : 'Could not update the budget.')
  }
}
function remove(b: Budget) {
  selected.value = null
  dialog.danger({
    title: `Delete ${b.budget_name}?`,
    message: 'Your transactions are not affected. Only the budget and its alerts are removed.',
    confirmLabel: 'Delete',
    onConfirm: async () => {
      try {
        await budgetsApi.remove(b.name)
        toast.success('Budget deleted')
        finance.dataVersion++
      } catch (e) {
        throw new Error(e instanceof ApiError ? e.message : 'Could not delete the budget.')
      }
    },
  })
}
</script>

<template>
  <div>
    <PageHeader title="Budgets">
      <template #actions>
        <button type="button" class="inline-flex h-10 items-center gap-1.5 rounded-full bg-brand-solid px-4 text-sm font-semibold text-white" @click="openCreate">
          <AppIcon name="plus" class="size-4" /> New budget
        </button>
      </template>
    </PageHeader>

    <div class="mb-4 flex items-center gap-2">
      <button type="button" class="inline-flex size-9 items-center justify-center rounded-full ring-1 ring-line hover:bg-card" aria-label="Previous month" @click="shift(-1)">
        <AppIcon name="chevron-left" class="size-4" />
      </button>
      <h2 class="min-w-[9rem] text-center font-semibold text-ink" aria-live="polite">{{ monthLabel }}</h2>
      <button type="button" class="inline-flex size-9 items-center justify-center rounded-full ring-1 ring-line hover:bg-card disabled:opacity-40" aria-label="Next month" :disabled="isCurrentMonth" @click="shift(1)">
        <AppIcon name="chevron-right" class="size-4" />
      </button>
      <button v-if="!isCurrentMonth" type="button" class="ml-1 text-sm font-medium text-brand-ink hover:underline" @click="month = new Date(now.getFullYear(), now.getMonth(), 1)">This month</button>
    </div>

    <p v-if="savedAt" class="mb-3 text-sm text-ink-muted">Showing budgets saved on this device at {{ new Date(savedAt).toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' }) }}.</p>
    <ErrorState v-if="error && !budgets.length" :message="error" :retrying="loading" @retry="load" />
    <div v-else-if="loading && !budgets.length" class="rounded-card bg-card px-3 ring-1 ring-line/60"><SkeletonRows :rows="4" /></div>

    <div v-else-if="!budgets.length" class="rounded-card bg-card ring-1 ring-line/60">
      <EmptyState icon="chart-pie" title="No budgets yet" message="Set a monthly limit for all spending or for categories like Food or Shopping. You'll be alerted before you overspend.">
        <button type="button" class="h-10 rounded-full bg-brand-solid px-5 text-sm font-semibold text-white" @click="openCreate">Create a budget</button>
      </EmptyState>
    </div>

    <template v-else>
      <AppCard v-if="overall?.progress" padding="lg" class="mb-4 cursor-pointer" @click="selected = overall">
        <div class="flex items-center gap-5">
          <ProgressRing :percent="overall.progress.percent" :size="104" :stroke="11" :label="`Overall budget ${Math.round(overall.progress.percent ?? 0)}% used`" />
          <div class="min-w-0">
            <p class="text-sm text-ink-muted">{{ overall.budget_name }}</p>
            <p v-if="overall.progress.remaining >= 0" class="text-ink"><Money :value="overall.progress.remaining" size="xl" /> <span class="text-ink-muted">left to spend</span></p>
            <p v-else class="text-expense"><Money :value="-overall.progress.remaining" size="xl" /> <span>over budget</span></p>
            <p class="mt-1 text-sm text-ink-muted"><Money :value="overall.progress.spent" size="sm" /> of <Money :value="overall.progress.available" size="sm" hide-fraction /> spent</p>
          </div>
        </div>
      </AppCard>

      <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3" :class="{ 'opacity-60': loading }">
        <BudgetCard v-for="b in active" :key="b.name" :budget="b" @select="selected = b" />
      </div>

      <section v-if="paused.length" class="mt-8">
        <h2 class="mb-3 text-sm font-semibold text-ink-muted">Paused</h2>
        <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <BudgetCard v-for="b in paused" :key="b.name" :budget="b" @select="selected = b" />
        </div>
      </section>
    </template>

    <ResponsiveSheet v-model:open="detailOpen" :title="selected?.budget_name" size="md">
      <div v-if="selected" class="pb-2">
        <div v-if="selected.progress" class="flex flex-col items-center py-2">
          <ProgressRing :percent="selected.progress.percent" :size="132" :stroke="12" :label="`${Math.round(selected.progress.percent ?? 0)}% used`" />
          <p class="mt-3 text-sm text-ink-muted">
            <Money :value="selected.progress.spent" size="sm" class="text-ink" /> of <Money :value="selected.progress.available" size="sm" hide-fraction class="text-ink" /> spent
          </p>
        </div>
        <section v-if="history.length" class="mt-4">
          <h3 class="mb-2 text-sm font-medium text-ink">Last 6 months</h3>
          <ul class="space-y-2.5">
            <li v-for="h in history" :key="h.month" class="grid grid-cols-[3.5rem_1fr_auto] items-center gap-3 text-sm">
              <span class="text-ink-muted">{{ monthShort(h.month) }}</span>
              <ProgressBar :percent="h.percent" :label="`${monthShort(h.month)}: ${Math.round(h.percent ?? 0)}% used`" height="sm" />
              <Money :value="h.spent" size="sm" hide-fraction class="text-ink" />
            </li>
          </ul>
        </section>
        <div class="mt-5 space-y-1">
          <RouterLink v-if="selected.category" :to="{ name: 'transactions', query: { category: selected.category, range: 'this_month' } }" class="flex h-12 items-center gap-3 rounded-tile px-3 text-[15px] text-ink hover:bg-ink/[0.04]" @click="selected = null">
            <AppIcon name="calendar" class="size-5 text-ink-muted" /> View transactions
          </RouterLink>
          <button type="button" class="flex h-12 w-full items-center gap-3 rounded-tile px-3 text-[15px] text-ink hover:bg-ink/[0.04]" @click="openEdit(selected)">
            <AppIcon name="pencil" class="size-5 text-ink-muted" /> Edit
          </button>
          <button type="button" class="flex h-12 w-full items-center gap-3 rounded-tile px-3 text-[15px] text-ink hover:bg-ink/[0.04]" @click="toggleActive(selected)">
            <AppIcon :name="selected.is_active ? 'archive' : 'rotate-ccw'" class="size-5 text-ink-muted" /> {{ selected.is_active ? 'Pause' : 'Resume' }}
          </button>
          <button type="button" class="flex h-12 w-full items-center gap-3 rounded-tile px-3 text-[15px] text-expense hover:bg-expense-soft/40" @click="remove(selected)">
            <AppIcon name="trash-2" class="size-5" /> Delete
          </button>
        </div>
      </div>
    </ResponsiveSheet>

    <ResponsiveSheet v-model:open="formOpen" :title="editing ? 'Edit budget' : 'New budget'" size="xl">
      <BudgetForm v-if="formOpen" :budget="editing" @saved="formOpen = false" @cancel="formOpen = false" />
    </ResponsiveSheet>
  </div>
</template>
