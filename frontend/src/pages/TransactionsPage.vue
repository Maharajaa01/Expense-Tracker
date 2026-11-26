<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '@/components/ui/AppIcon.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import Money from '@/components/ui/Money.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import ResponsiveSheet from '@/components/ui/ResponsiveSheet.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import SelectField from '@/components/ui/SelectField.vue'
import SkeletonRows from '@/components/ui/SkeletonRows.vue'
import TransactionRow from '@/components/ui/TransactionRow.vue'
import { useDebounced } from '@/composables/useDebounced'
import TransactionDetail from '@/features/transactions/TransactionDetail.vue'
import { RANGE_OPTIONS, rangeDates, type RangeKey } from '@/features/transactions/dateRanges'
import { useTransactionList } from '@/features/transactions/useTransactionList'
import { ioApi } from '@/services/finance'
import { useFinanceStore } from '@/stores/finance'
import { useUiStore } from '@/stores/ui'
import type { SortKey, TransactionFilters, TransactionRowData, TransactionType } from '@/types/finance'
import { dayLabel } from '@/utils/date'

const route = useRoute()
const router = useRouter()
const finance = useFinanceStore()
const ui = useUiStore()

// Filter state mirrors the URL so filtered views can be linked and survive reloads.
const q = ref(String(route.query.q ?? ''))
const type = ref<'' | TransactionType>((route.query.type as TransactionType) ?? '')
const account = ref(String(route.query.account ?? ''))
const category = ref(String(route.query.category ?? ''))
const range = ref<RangeKey>((route.query.range as RangeKey) ?? (route.query.from_date ? 'custom' : 'all'))
const fromDate = ref(String(route.query.from_date ?? ''))
const toDate = ref(String(route.query.to_date ?? ''))
const sort = ref<SortKey>((route.query.sort as SortKey) ?? 'date_desc')
const toCategorise = ref(route.query.review === '1')
const showFilters = ref(false)
const debouncedQ = useDebounced(q, 300)

const filters = computed<TransactionFilters>(() => {
  const dates = range.value === 'custom' ? { from_date: fromDate.value, to_date: toDate.value } : rangeDates(range.value)
  return { q: debouncedQ.value, type: type.value, account: account.value, category: category.value, ...dates, ...(toCategorise.value ? { needs_review: 1 as const } : {}) }
})

watch([debouncedQ, type, account, category, range, fromDate, toDate, sort, toCategorise], () => {
  const query: Record<string, string> = {}
  if (debouncedQ.value) query.q = debouncedQ.value
  if (type.value) query.type = type.value
  if (account.value) query.account = account.value
  if (category.value) query.category = category.value
  if (range.value !== 'all') query.range = range.value
  if (range.value === 'custom') Object.assign(query, { from_date: fromDate.value, to_date: toDate.value })
  if (sort.value !== 'date_desc') query.sort = sort.value
  if (toCategorise.value) query.review = '1'
  router.replace({ query })
})

const list = useTransactionList(filters, sort)
onMounted(() => finance.load())

const activeFilterCount = computed(
  () => [type.value, account.value, category.value, range.value !== 'all' ? 'r' : '', toCategorise.value ? 'c' : ''].filter(Boolean).length,
)
function clearFilters() {
  type.value = ''
  account.value = ''
  category.value = ''
  range.value = 'all'
  toCategorise.value = false
  q.value = ''
}

const typeOptions = [
  { value: '' as const, label: 'All' },
  { value: 'Expense' as const, label: 'Expenses' },
  { value: 'Income' as const, label: 'Income' },
  { value: 'Transfer' as const, label: 'Transfers' },
]
const accountOptions = computed(() =>
  finance.accounts.map((a) => ({ value: a.name, label: a.is_archived ? `${a.account_name} (archived)` : a.account_name })),
)
const categoryOptions = computed(() => {
  const out: { value: string; label: string }[] = []
  for (const t of ['Expense', 'Income'] as const) {
    if (type.value && type.value !== t) continue
    for (const p of finance.categoryTree(t, true)) {
      out.push({ value: p.name, label: p.category_name })
      for (const c of p.children) out.push({ value: c.name, label: `  ${p.category_name} › ${c.category_name}` })
    }
  }
  return out
})
const sortOptions = [
  { value: 'date_desc', label: 'Newest first' },
  { value: 'date_asc', label: 'Oldest first' },
  { value: 'amount_desc', label: 'Largest amount' },
  { value: 'amount_asc', label: 'Smallest amount' },
]

// Detail sheet
const selected = ref<TransactionRowData | null>(null)
const detailOpen = computed({ get: () => !!selected.value, set: (v) => !v && (selected.value = null) })

// Infinite scroll, with the button as a fallback.
const sentinel = ref<HTMLElement>()
let observer: IntersectionObserver | undefined
onMounted(() => {
  observer = new IntersectionObserver((entries) => entries[0]?.isIntersecting && list.loadMore(), { rootMargin: '400px' })
  if (sentinel.value) observer.observe(sentinel.value)
})
onBeforeUnmount(() => observer?.disconnect())

const filteredAccount = computed(() => (account.value ? finance.accountMap.get(account.value) : null))
</script>

<template>
  <div>
    <PageHeader
      :title="filteredAccount ? filteredAccount.account_name : 'Transactions'"
      :subtitle="filteredAccount ? 'Account history' : undefined"
    >
      <template #actions>
        <a
          :href="ioApi.exportUrl(filters)"
          download
          class="inline-flex h-10 items-center gap-1.5 rounded-full px-4 text-sm font-medium text-ink ring-1 ring-line hover:bg-card"
          title="Download the transactions matching these filters as CSV"
        >
          <AppIcon name="download" class="size-4" /> Export
        </a>
        <button
          type="button"
          class="hidden h-10 items-center gap-1.5 rounded-full bg-brand-solid px-4 text-sm font-semibold text-white lg:inline-flex"
          @click="ui.openQuickAdd('Expense', account || null)"
        >
          <AppIcon name="plus" class="size-4" /> Add
        </button>
      </template>
    </PageHeader>

    <!-- Search + filters -->
    <div class="mb-4 space-y-3">
      <div class="flex gap-2">
        <label class="relative flex-1">
          <span class="sr-only">Search transactions</span>
          <AppIcon name="search" class="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-ink-faint" />
          <input
            v-model="q"
            type="search"
            placeholder="Search transactions"
            title="Search by description, category or amount"
            class="h-11 w-full rounded-full border-0 bg-card pl-10 pr-4 text-[15px] text-ink ring-1 ring-line placeholder:text-ink-faint focus:ring-2 focus:ring-brand"
          />
        </label>
        <button
          type="button"
          class="relative inline-flex h-11 items-center gap-1.5 rounded-full bg-card px-4 text-sm font-medium text-ink ring-1 ring-line lg:hidden"
          :aria-expanded="showFilters"
          aria-controls="txn-filters"
          @click="showFilters = !showFilters"
        >
          <AppIcon name="filter" class="size-4" />
          Filters
          <span v-if="activeFilterCount" class="ml-0.5 rounded-full bg-brand-solid px-1.5 text-[11px] font-semibold text-white">{{ activeFilterCount }}</span>
        </button>
      </div>

      <div id="txn-filters" class="space-y-3 rounded-card bg-card p-3 ring-1 ring-line/60 lg:block" :class="showFilters ? 'block' : 'hidden'">
        <SegmentedControl v-model="type" :options="typeOptions" label="Transaction type" size="sm" />
        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <SelectField v-model="account" label="Account" :options="accountOptions" placeholder="All accounts" />
          <SelectField v-model="category" label="Category" :options="categoryOptions" placeholder="All categories" />
          <SelectField v-model="range" label="Date" :options="RANGE_OPTIONS" />
          <SelectField v-model="sort" label="Sort" :options="sortOptions" />
        </div>
        <div v-if="range === 'custom'" class="grid grid-cols-2 gap-3">
          <label class="block text-sm">
            <span class="mb-1.5 block font-medium text-ink">From</span>
            <input v-model="fromDate" type="date" class="h-10 w-full rounded-[10px] border-0 bg-card px-3 text-ink ring-1 ring-line focus:ring-2 focus:ring-brand" />
          </label>
          <label class="block text-sm">
            <span class="mb-1.5 block font-medium text-ink">To</span>
            <input v-model="toDate" type="date" :min="fromDate" class="h-10 w-full rounded-[10px] border-0 bg-card px-3 text-ink ring-1 ring-line focus:ring-2 focus:ring-brand" />
          </label>
        </div>
        <label class="inline-flex items-center gap-2 text-sm text-ink">
          <input v-model="toCategorise" type="checkbox" class="size-4 rounded text-brand-solid focus:ring-brand" />
          Only payments to categorise
        </label>
        <button v-if="activeFilterCount || q" type="button" class="ml-4 text-sm font-medium text-brand-ink hover:underline" @click="clearFilters">
          Clear filters
        </button>
      </div>
    </div>

    <p v-if="list.savedAt.value" class="mb-3 text-sm text-ink-muted">
      Showing transactions saved on this device at {{ new Date(list.savedAt.value).toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' }) }}.
    </p>
    <!-- Result summary -->
    <p v-if="list.summary.value && !list.loading.value && list.total.value" class="mb-3 text-sm text-ink-muted">
      {{ list.total.value }} {{ list.total.value === 1 ? 'transaction' : 'transactions' }}:
      <Money :value="list.summary.value.expense" size="sm" class="text-ink" /> spent,
      <Money :value="list.summary.value.income" size="sm" class="text-ink" /> received
    </p>

    <ErrorState v-if="list.error.value && !list.rows.value.length" :message="list.error.value" :retrying="list.loading.value" @retry="list.reload" />

    <div v-else-if="list.loading.value && !list.rows.value.length" class="rounded-card bg-card px-3 ring-1 ring-line/60">
      <SkeletonRows :rows="6" />
    </div>

    <div v-else-if="!list.rows.value.length" class="rounded-card bg-card ring-1 ring-line/60">
      <EmptyState
        v-if="activeFilterCount || q"
        icon="search"
        title="No matching transactions"
        message="Try a different search or clear the filters."
      >
        <button type="button" class="text-sm font-medium text-brand-ink hover:underline" @click="clearFilters">Clear filters</button>
      </EmptyState>
      <EmptyState v-else icon="inbox" title="No transactions yet" message="Record your first expense or income to see it here.">
        <button type="button" class="h-10 rounded-full bg-brand-solid px-5 text-sm font-semibold text-white" @click="ui.openQuickAdd()">
          Add transaction
        </button>
      </EmptyState>
    </div>

    <div v-else :class="{ 'opacity-60 transition-opacity': list.loading.value }">
      <!-- Grouped by day when sorted by date -->
      <template v-if="list.groups.value.length">
        <section v-for="g in list.groups.value" :key="g.date" class="mb-4" :aria-label="dayLabel(g.date)">
          <header class="flex items-baseline justify-between px-2 pb-1.5">
            <h2 class="text-[13px] font-semibold text-ink-muted">{{ dayLabel(g.date) }}</h2>
            <span class="text-[13px] text-ink-faint">
              <span v-if="g.totals.expense"><Money :value="g.totals.expense" size="sm" /> spent</span><span v-if="g.totals.expense && g.totals.income">, </span><span v-if="g.totals.income"><Money :value="g.totals.income" size="sm" /> in</span>
            </span>
          </header>
          <div class="rounded-card bg-card p-1.5 ring-1 ring-line/60">
            <TransactionRow v-for="t in g.rows" :key="t.name" :txn="t" @select="selected = $event" />
          </div>
        </section>
      </template>
      <div v-else class="rounded-card bg-card p-1.5 ring-1 ring-line/60">
        <TransactionRow v-for="t in list.rows.value" :key="t.name" :txn="t" show-date @select="selected = $event" />
      </div>

      <div ref="sentinel" class="flex justify-center py-4">
        <button
          v-if="list.hasMore.value"
          type="button"
          class="inline-flex h-10 items-center gap-2 rounded-full px-5 text-sm font-medium text-ink ring-1 ring-line hover:bg-card disabled:opacity-60"
          :disabled="list.loadingMore.value"
          @click="list.loadMore"
        >
          <AppIcon v-if="list.loadingMore.value" name="refresh-cw" class="size-4 animate-spin" />
          Load more
        </button>
        <p v-else-if="list.error.value" class="text-sm text-expense">{{ list.error.value }}</p>
        <p v-else-if="list.rows.value.length > 10" class="text-sm text-ink-faint">That's everything.</p>
      </div>
    </div>

    <ResponsiveSheet v-model:open="detailOpen" title="Transaction" size="md">
      <TransactionDetail v-if="selected" :txn="selected" @close="selected = null" />
    </ResponsiveSheet>
  </div>
</template>
