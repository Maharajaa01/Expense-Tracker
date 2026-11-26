<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { dialog, toast } from 'frappe-ui'
import AppIcon from '@/components/ui/AppIcon.vue'
import CategoryIcon from '@/components/ui/CategoryIcon.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import Money from '@/components/ui/Money.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import ProgressRing from '@/components/ui/ProgressRing.vue'
import ResponsiveSheet from '@/components/ui/ResponsiveSheet.vue'
import SkeletonRows from '@/components/ui/SkeletonRows.vue'
import ContributionForm from '@/features/goals/ContributionForm.vue'
import GoalForm from '@/features/goals/GoalForm.vue'
import { ApiError } from '@/services/api'
import { goalsApi } from '@/services/finance'
import { useFinanceStore } from '@/stores/finance'
import type { Goal } from '@/types/finance'
import { dayLabel, fromISO } from '@/utils/date'

const finance = useFinanceStore()
const goals = ref<Goal[]>([])
const showArchived = ref(false)
const loading = ref(true)
const error = ref<string | null>(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    goals.value = await goalsApi.list(true)
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Could not load goals.'
  } finally {
    loading.value = false
  }
}
onMounted(() => {
  finance.load()
  load()
})
watch(() => finance.dataVersion, load)

const current = computed(() => goals.value.filter((g) => g.status !== 'Archived'))
const archived = computed(() => goals.value.filter((g) => g.status === 'Archived'))
const byDate = (iso: string) => new Intl.DateTimeFormat('en-IN', { month: 'short', year: 'numeric' }).format(fromISO(iso))

const selected = ref<Goal | null>(null)
const detailOpen = computed({ get: () => !!selected.value, set: (v) => !v && (selected.value = null) })
watch(goals, (list) => {
  if (selected.value) selected.value = list.find((g) => g.name === selected.value!.name) ?? null
})
const formOpen = ref(false)
const editing = ref<Goal | null>(null)
const contributeFor = ref<{ goal: Goal; kind: 'Contribution' | 'Withdrawal' } | null>(null)
const contributeOpen = computed({ get: () => !!contributeFor.value, set: (v) => !v && (contributeFor.value = null) })

function openCreate() {
  editing.value = null
  formOpen.value = true
}
function openEdit(g: Goal) {
  selected.value = null
  editing.value = g
  formOpen.value = true
}
async function setStatus(g: Goal, archived: boolean) {
  try {
    await goalsApi.update(g.name, { status: archived ? 'Archived' : 'Active' })
    toast.success(archived ? 'Goal archived' : 'Goal restored')
    selected.value = null
    finance.dataVersion++
  } catch (e) {
    toast.error(e instanceof ApiError ? e.message : 'Could not update the goal.')
  }
}
function undo(g: Goal, rowName: string) {
  dialog.danger({
    title: 'Remove this entry?',
    message: 'If it moved money between accounts, that transfer is removed too and balances are recalculated.',
    confirmLabel: 'Remove',
    onConfirm: async () => {
      try {
        await goalsApi.removeContribution(g.name, rowName)
        toast.success('Entry removed')
        await finance.changed()
      } catch (e) {
        throw new Error(e instanceof ApiError ? e.message : 'Could not remove it.')
      }
    },
  })
}
function remove(g: Goal) {
  selected.value = null
  dialog.danger({
    title: `Delete ${g.goal_name}?`,
    message: 'The goal and its tracked contributions are deleted. This cannot be undone.',
    confirmLabel: 'Delete',
    onConfirm: async () => {
      try {
        await goalsApi.remove(g.name)
        toast.success('Goal deleted')
        finance.dataVersion++
      } catch (e) {
        throw new Error(e instanceof ApiError ? e.message : 'Could not delete the goal.')
      }
    },
  })
}
</script>

<template>
  <div>
    <PageHeader title="Savings goals">
      <template #actions>
        <button type="button" class="inline-flex h-10 items-center gap-1.5 rounded-full bg-brand-solid px-4 text-sm font-semibold text-white" @click="openCreate">
          <AppIcon name="plus" class="size-4" /> New goal
        </button>
      </template>
    </PageHeader>

    <ErrorState v-if="error && !goals.length" :message="error" :retrying="loading" @retry="load" />
    <div v-else-if="loading && !goals.length" class="rounded-card bg-card px-3 ring-1 ring-line/60"><SkeletonRows :rows="3" /></div>
    <div v-else-if="!current.length && !archived.length" class="rounded-card bg-card ring-1 ring-line/60">
      <EmptyState icon="piggy-bank" title="No savings goals yet" message="Saving for a bike, a trip or an emergency fund? Set a target and watch it grow.">
        <button type="button" class="h-10 rounded-full bg-brand-solid px-5 text-sm font-semibold text-white" @click="openCreate">Create a goal</button>
      </EmptyState>
    </div>

    <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      <article v-for="g in current" :key="g.name" class="flex flex-col rounded-card bg-card p-4 ring-1 ring-line/60">
        <button type="button" class="flex items-center gap-4 text-left" @click="selected = g">
          <ProgressRing :percent="g.percent" tone="savings" :size="76" :stroke="8" :label="`${g.goal_name}: ${Math.round(g.percent ?? 0)}% saved`">
            <CategoryIcon :icon="g.icon" :color="g.color" size="sm" />
          </ProgressRing>
          <span class="min-w-0 flex-1">
            <span class="flex items-center gap-1.5">
              <span class="truncate font-semibold text-ink">{{ g.goal_name }}</span>
              <span v-if="g.status === 'Achieved'" class="rounded-full bg-savings-soft px-2 py-0.5 text-[11px] font-semibold text-savings">Reached</span>
            </span>
            <span class="block text-ink"><Money :value="g.current_amount" size="lg" /></span>
            <span class="block text-[13px] text-ink-muted">of <Money :value="g.target_amount" size="sm" hide-fraction />, {{ Math.round(g.percent ?? 0) }}%</span>
          </span>
        </button>
        <p class="mt-3 text-[13px] text-ink-muted">
          <template v-if="g.remaining <= 0">Target reached.</template>
          <template v-else-if="g.monthly_needed">Save <Money :value="g.monthly_needed" size="sm" hide-fraction class="font-semibold text-ink" /> a month to reach it by {{ byDate(g.target_date!) }}.</template>
          <template v-else-if="g.target_date && (g.days_left ?? 0) <= 0"><Money :value="g.remaining" size="sm" hide-fraction class="font-semibold text-ink" /> to go; the target date has passed.</template>
          <template v-else><Money :value="g.remaining" size="sm" hide-fraction class="font-semibold text-ink" /> to go.</template>
        </p>
        <div class="mt-4 flex gap-2">
          <button type="button" class="h-10 flex-1 rounded-full bg-brand-solid text-sm font-semibold text-white" @click="contributeFor = { goal: g, kind: 'Contribution' }">Add money</button>
          <button type="button" class="h-10 rounded-full px-4 text-sm font-medium text-ink ring-1 ring-line hover:bg-ink/[0.03] disabled:opacity-40" :disabled="g.current_amount <= 0" @click="contributeFor = { goal: g, kind: 'Withdrawal' }">Withdraw</button>
        </div>
      </article>
    </div>

    <section v-if="archived.length" class="mt-8">
      <button type="button" class="mb-3 inline-flex items-center gap-1 text-sm font-medium text-ink-muted hover:text-ink" :aria-expanded="showArchived" @click="showArchived = !showArchived">
        <AppIcon name="chevron-right" class="size-4 transition-transform" :class="{ 'rotate-90': showArchived }" /> Archived ({{ archived.length }})
      </button>
      <div v-if="showArchived" class="rounded-card bg-card p-1.5 ring-1 ring-line/60">
        <button v-for="g in archived" :key="g.name" type="button" class="flex w-full items-center gap-3 rounded-tile px-2 py-2.5 text-left opacity-75 hover:bg-ink/[0.03]" @click="selected = g">
          <CategoryIcon :icon="g.icon" :color="g.color" size="sm" />
          <span class="flex-1 text-[15px] text-ink">{{ g.goal_name }}</span>
          <Money :value="g.current_amount" size="sm" tone="muted" />
        </button>
      </div>
    </section>

    <ResponsiveSheet v-model:open="detailOpen" :title="selected?.goal_name" size="md">
      <div v-if="selected" class="pb-2">
        <div class="flex flex-col items-center py-2">
          <ProgressRing :percent="selected.percent" tone="savings" :size="120" :stroke="11" :label="`${Math.round(selected.percent ?? 0)}% saved`" />
          <p class="mt-3 text-sm text-ink-muted"><Money :value="selected.current_amount" size="sm" class="text-ink" /> of <Money :value="selected.target_amount" size="sm" hide-fraction class="text-ink" /></p>
          <p v-if="selected.linked_account_name" class="mt-1 text-[13px] text-ink-muted">Kept in {{ selected.linked_account_name }}</p>
        </div>
        <section class="mt-3">
          <h3 class="mb-2 text-sm font-medium text-ink">History</h3>
          <p v-if="!selected.contributions.length" class="text-sm text-ink-muted">Nothing added yet.</p>
          <ul class="divide-y divide-line/60 rounded-tile ring-1 ring-line/60">
            <li v-for="c in selected.contributions" :key="c.name" class="flex items-center gap-3 px-3 py-2.5 text-sm">
              <span class="min-w-0 flex-1">
                <span class="block text-ink">{{ c.kind === 'Contribution' ? 'Added' : 'Withdrawn' }}<template v-if="c.note">, {{ c.note }}</template></span>
                <span class="block text-[12.5px] text-ink-muted">{{ dayLabel(c.date) }}{{ c.transaction ? ', transfer' : '' }}</span>
              </span>
              <Money :value="c.kind === 'Contribution' ? c.amount : -c.amount" :sign="c.kind === 'Contribution' ? 'always' : 'auto'" size="sm" class="text-ink" />
              <button type="button" class="text-ink-faint hover:text-expense" :aria-label="`Remove entry of ${c.amount}`" @click="undo(selected!, c.name)">
                <AppIcon name="x" class="size-4" />
              </button>
            </li>
          </ul>
        </section>
        <div class="mt-4 space-y-1">
          <button type="button" class="flex h-12 w-full items-center gap-3 rounded-tile px-3 text-[15px] text-ink hover:bg-ink/[0.04]" @click="openEdit(selected)"><AppIcon name="pencil" class="size-5 text-ink-muted" /> Edit</button>
          <button type="button" class="flex h-12 w-full items-center gap-3 rounded-tile px-3 text-[15px] text-ink hover:bg-ink/[0.04]" @click="setStatus(selected, selected.status !== 'Archived')">
            <AppIcon :name="selected.status === 'Archived' ? 'rotate-ccw' : 'archive'" class="size-5 text-ink-muted" /> {{ selected.status === 'Archived' ? 'Restore' : 'Archive' }}
          </button>
          <button v-if="!selected.contributions.some((c) => c.transaction)" type="button" class="flex h-12 w-full items-center gap-3 rounded-tile px-3 text-[15px] text-expense hover:bg-expense-soft/40" @click="remove(selected)">
            <AppIcon name="trash-2" class="size-5" /> Delete
          </button>
        </div>
      </div>
    </ResponsiveSheet>

    <ResponsiveSheet v-model:open="formOpen" :title="editing ? 'Edit goal' : 'New goal'" size="xl">
      <GoalForm v-if="formOpen" :goal="editing" @saved="formOpen = false" @cancel="formOpen = false" />
    </ResponsiveSheet>
    <ResponsiveSheet v-model:open="contributeOpen" :title="contributeFor?.goal.goal_name" size="md">
      <ContributionForm v-if="contributeFor" :goal="contributeFor.goal" :kind="contributeFor.kind" @saved="contributeFor = null" @cancel="contributeFor = null" />
    </ResponsiveSheet>
  </div>
</template>
