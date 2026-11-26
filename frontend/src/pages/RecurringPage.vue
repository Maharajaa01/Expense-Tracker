<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { dialog, toast } from 'frappe-ui'
import AppIcon from '@/components/ui/AppIcon.vue'
import CategoryIcon from '@/components/ui/CategoryIcon.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import Money from '@/components/ui/Money.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import ResponsiveSheet from '@/components/ui/ResponsiveSheet.vue'
import SkeletonRows from '@/components/ui/SkeletonRows.vue'
import RecurringForm from '@/features/recurring/RecurringForm.vue'
import { ApiError } from '@/services/api'
import { recurringApi } from '@/services/finance'
import { useFinanceStore } from '@/stores/finance'
import type { Recurring, UpcomingPayment } from '@/types/finance'
import { dayLabel } from '@/utils/date'
import { formatMoney } from '@/utils/money'

const finance = useFinanceStore()
const items = ref<Recurring[]>([])
const upcoming = ref<UpcomingPayment[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const busy = ref<string | null>(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    ;[items.value, upcoming.value] = await Promise.all([recurringApi.list(), recurringApi.upcoming(30)])
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Could not load recurring payments.'
  } finally {
    loading.value = false
  }
}
onMounted(() => {
  finance.load()
  load()
})
watch(() => finance.dataVersion, load)

const active = computed(() => items.value.filter((r) => r.is_active))
const inactive = computed(() => items.value.filter((r) => !r.is_active))
const byName = computed(() => new Map(items.value.map((r) => [r.name, r])))

const selected = ref<Recurring | null>(null)
const detailOpen = computed({ get: () => !!selected.value, set: (v) => !v && (selected.value = null) })
const formOpen = ref(false)
const editing = ref<Recurring | null>(null)
function openCreate() {
  editing.value = null
  formOpen.value = true
}
function openEdit(r: Recurring) {
  selected.value = null
  editing.value = r
  formOpen.value = true
}

async function act(r: Recurring, action: 'post' | 'skip' | 'toggle') {
  if (busy.value) return
  busy.value = r.name
  try {
    if (action === 'post') {
      await recurringApi.postNow(r.name)
      toast.success(`${r.title} recorded`)
      await finance.changed()
    } else if (action === 'skip') {
      await recurringApi.skipNext(r.name)
      toast.success('Skipped the next payment')
      finance.dataVersion++
    } else {
      await recurringApi.update(r.name, { is_active: r.is_active ? 0 : 1 })
      toast.success(r.is_active ? 'Paused' : 'Resumed')
      finance.dataVersion++
    }
    selected.value = null
  } catch (e) {
    toast.error(e instanceof ApiError ? e.message : 'Something went wrong.')
  } finally {
    busy.value = null
  }
}
function remove(r: Recurring) {
  selected.value = null
  dialog.danger({
    title: `Delete ${r.title}?`,
    message: 'Future payments stop. Transactions it already added stay in your history.',
    confirmLabel: 'Delete',
    onConfirm: async () => {
      try {
        await recurringApi.remove(r.name)
        toast.success('Recurring payment deleted')
        finance.dataVersion++
      } catch (e) {
        throw new Error(e instanceof ApiError ? e.message : 'Could not delete.')
      }
    },
  })
}
const signed = (t: string, a: number) => (t === 'Income' ? a : t === 'Transfer' ? a : -a)
const statusOf = (r: Recurring) => (!r.next_run_date ? 'Finished' : r.is_active ? null : 'Paused')
</script>

<template>
  <div>
    <PageHeader title="Recurring payments" subtitle="Salary, rent, bills and subscriptions that repeat.">
      <template #actions>
        <button type="button" class="inline-flex h-10 items-center gap-1.5 rounded-full bg-brand-solid px-4 text-sm font-semibold text-white" @click="openCreate">
          <AppIcon name="plus" class="size-4" /> Add
        </button>
      </template>
    </PageHeader>

    <ErrorState v-if="error && !items.length" :message="error" :retrying="loading" @retry="load" />
    <div v-else-if="loading && !items.length" class="rounded-card bg-card px-3 ring-1 ring-line/60"><SkeletonRows :rows="4" /></div>
    <div v-else-if="!items.length" class="rounded-card bg-card ring-1 ring-line/60">
      <EmptyState icon="calendar-sync" title="No recurring payments" message="Add rent, EMIs, subscriptions or your salary once. They're recorded for you when they're due, and you're reminded before.">
        <button type="button" class="h-10 rounded-full bg-brand-solid px-5 text-sm font-semibold text-white" @click="openCreate">Add recurring payment</button>
      </EmptyState>
    </div>

    <template v-else>
      <section class="mb-6">
        <h2 class="mb-2 px-1 text-sm font-semibold text-ink-muted">Next 30 days</h2>
        <div class="rounded-card bg-card p-1.5 ring-1 ring-line/60">
          <p v-if="!upcoming.length" class="px-3 py-6 text-center text-sm text-ink-muted">Nothing due in the next 30 days.</p>
          <div v-for="u in upcoming" :key="`${u.recurring}-${u.date}`" class="flex items-center gap-3 rounded-tile px-2 py-2.5">
            <div class="w-14 shrink-0 text-center">
              <p class="text-[13px] font-semibold" :class="u.overdue ? 'text-expense' : 'text-ink'">{{ u.overdue ? 'Overdue' : dayLabel(u.date).replace(/^\w+, /, '') }}</p>
            </div>
            <CategoryIcon :icon="byName.get(u.recurring)?.category_icon ?? (u.transaction_type === 'Transfer' ? 'arrow-left-right' : 'calendar-sync')" :color="byName.get(u.recurring)?.category_color ?? '#7c3aed'" size="sm" />
            <span class="min-w-0 flex-1">
              <span class="block truncate text-[15px] font-medium text-ink">{{ u.title }}</span>
              <span class="block text-[13px] text-ink-muted">{{ u.auto_post ? 'Added automatically' : 'Needs your confirmation' }}</span>
            </span>
            <Money :value="signed(u.transaction_type, u.amount)" :sign="u.transaction_type === 'Income' ? 'always' : 'auto'" :tone="u.transaction_type === 'Income' ? 'income' : u.transaction_type === 'Transfer' ? 'muted' : 'expense'" size="sm" />
            <button
              v-if="!u.auto_post && (u.overdue || dayLabel(u.date) === 'Today') && byName.get(u.recurring)"
              type="button"
              class="ml-1 h-8 shrink-0 rounded-full bg-brand-solid px-3 text-[13px] font-semibold text-white disabled:opacity-60"
              :disabled="busy === u.recurring"
              @click="act(byName.get(u.recurring)!, 'post')"
            >
              Mark paid
            </button>
          </div>
        </div>
      </section>

      <section>
        <h2 class="mb-2 px-1 text-sm font-semibold text-ink-muted">All recurring payments</h2>
        <div class="rounded-card bg-card p-1.5 ring-1 ring-line/60">
          <button v-for="r in [...active, ...inactive]" :key="r.name" type="button" class="flex w-full items-center gap-3 rounded-tile px-2 py-2.5 text-left hover:bg-ink/[0.03]" :class="{ 'opacity-60': !r.is_active }" @click="selected = r">
            <CategoryIcon :icon="r.category_icon ?? (r.transaction_type === 'Transfer' ? 'arrow-left-right' : 'calendar-sync')" :color="r.category_color ?? '#7c3aed'" />
            <span class="min-w-0 flex-1">
              <span class="block truncate text-[15px] font-medium text-ink">{{ r.title }}</span>
              <span class="block truncate text-[13px] text-ink-muted">
                {{ r.schedule }}<template v-if="statusOf(r)">, {{ statusOf(r)?.toLowerCase() }}</template><template v-else-if="r.next_run_date">, next {{ dayLabel(r.next_run_date) }}</template>
              </span>
            </span>
            <Money :value="signed(r.transaction_type, r.amount)" :sign="r.transaction_type === 'Income' ? 'always' : 'auto'" :tone="r.transaction_type === 'Income' ? 'income' : r.transaction_type === 'Transfer' ? 'muted' : 'expense'" size="md" />
          </button>
        </div>
      </section>
    </template>

    <ResponsiveSheet v-model:open="detailOpen" :title="selected?.title" size="md">
      <div v-if="selected" class="pb-2">
        <dl class="mb-4 divide-y divide-line/60 rounded-tile ring-1 ring-line/60 text-sm">
          <div class="flex justify-between gap-3 px-4 py-3"><dt class="text-ink-muted">Amount</dt><dd class="font-medium text-ink">{{ formatMoney(selected.amount) }}</dd></div>
          <div class="flex justify-between gap-3 px-4 py-3"><dt class="text-ink-muted">Repeats</dt><dd class="font-medium text-ink">{{ selected.schedule }}</dd></div>
          <div class="flex justify-between gap-3 px-4 py-3"><dt class="text-ink-muted">Next</dt><dd class="font-medium text-ink">{{ selected.next_run_date ? dayLabel(selected.next_run_date) : 'No more payments' }}</dd></div>
          <div class="flex justify-between gap-3 px-4 py-3"><dt class="text-ink-muted">{{ selected.transaction_type === 'Transfer' ? 'Accounts' : 'Account' }}</dt><dd class="text-right font-medium text-ink">{{ selected.account_name }}<template v-if="selected.to_account_name"> to {{ selected.to_account_name }}</template></dd></div>
          <div v-if="selected.category_name" class="flex justify-between gap-3 px-4 py-3"><dt class="text-ink-muted">Category</dt><dd class="font-medium text-ink">{{ selected.category_name }}</dd></div>
          <div class="flex justify-between gap-3 px-4 py-3"><dt class="text-ink-muted">Recorded so far</dt><dd class="font-medium text-ink">{{ selected.occurrences_posted }}</dd></div>
        </dl>
        <div class="space-y-1">
          <button v-if="selected.is_active && selected.next_run_date" type="button" class="flex h-12 w-full items-center gap-3 rounded-tile px-3 text-[15px] text-ink hover:bg-ink/[0.04] disabled:opacity-60" :disabled="!!busy" @click="act(selected, 'post')">
            <AppIcon name="check" class="size-5 text-ink-muted" /> Record next payment now
          </button>
          <button v-if="selected.is_active && selected.next_run_date" type="button" class="flex h-12 w-full items-center gap-3 rounded-tile px-3 text-[15px] text-ink hover:bg-ink/[0.04] disabled:opacity-60" :disabled="!!busy" @click="act(selected, 'skip')">
            <AppIcon name="chevron-right" class="size-5 text-ink-muted" /> Skip next payment
          </button>
          <RouterLink :to="{ name: 'transactions', query: { q: selected.title } }" class="flex h-12 items-center gap-3 rounded-tile px-3 text-[15px] text-ink hover:bg-ink/[0.04]" @click="selected = null">
            <AppIcon name="calendar" class="size-5 text-ink-muted" /> View past payments
          </RouterLink>
          <button type="button" class="flex h-12 w-full items-center gap-3 rounded-tile px-3 text-[15px] text-ink hover:bg-ink/[0.04]" @click="openEdit(selected)">
            <AppIcon name="pencil" class="size-5 text-ink-muted" /> Edit
          </button>
          <button v-if="selected.next_run_date" type="button" class="flex h-12 w-full items-center gap-3 rounded-tile px-3 text-[15px] text-ink hover:bg-ink/[0.04] disabled:opacity-60" :disabled="!!busy" @click="act(selected, 'toggle')">
            <AppIcon :name="selected.is_active ? 'archive' : 'rotate-ccw'" class="size-5 text-ink-muted" /> {{ selected.is_active ? 'Pause' : 'Resume' }}
          </button>
          <button type="button" class="flex h-12 w-full items-center gap-3 rounded-tile px-3 text-[15px] text-expense hover:bg-expense-soft/40" @click="remove(selected)">
            <AppIcon name="trash-2" class="size-5" /> Delete
          </button>
        </div>
      </div>
    </ResponsiveSheet>

    <ResponsiveSheet v-model:open="formOpen" :title="editing ? 'Edit recurring payment' : 'New recurring payment'" size="xl">
      <RecurringForm v-if="formOpen" :recurring="editing" @saved="formOpen = false" @cancel="formOpen = false" />
    </ResponsiveSheet>
  </div>
</template>
