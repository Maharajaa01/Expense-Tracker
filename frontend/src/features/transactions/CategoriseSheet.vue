<script setup lang="ts">
/**
 * "To categorise": entries created from bank alerts, one at a time.
 * Tap a category → saved → next. The choice is remembered for the payee.
 */
import { computed, onMounted, ref } from 'vue'
import { toast } from 'frappe-ui'
import AppIcon from '@/components/ui/AppIcon.vue'
import CategoryIcon from '@/components/ui/CategoryIcon.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Money from '@/components/ui/Money.vue'
import { ApiError } from '@/services/api'
import { transactionsApi } from '@/services/finance'
import { useFinanceStore } from '@/stores/finance'
import type { TransactionRowData } from '@/types/finance'
import { isUncategorised } from '@/utils/categories'
import { dayLabel } from '@/utils/date'

const emit = defineEmits<{ done: [] }>()
const finance = useFinanceStore()
const queue = ref<TransactionRowData[]>([])
const index = ref(0)
const loading = ref(true)
const saving = ref(false)
const error = ref<string | null>(null)
const doneCount = ref(0)

async function load() {
  loading.value = true
  try {
    await finance.load()
    queue.value = (await transactionsApi.list({ needs_review: 1 }, 1, 100, 'date_desc')).rows
    index.value = 0
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Could not load entries.'
  } finally {
    loading.value = false
  }
}
onMounted(load)

const current = computed(() => queue.value[index.value] ?? null)
const options = computed(() =>
  current.value && current.value.transaction_type !== 'Transfer'
    ? finance.categoryTree(current.value.transaction_type).filter((c) => !isUncategorised(c))
    : [],
)

async function choose(category: string) {
  const t = current.value
  if (!t || saving.value) return
  saving.value = true
  error.value = null
  try {
    await transactionsApi.update(t.name, { category }, t.modified)
    doneCount.value++
    index.value++
    if (!current.value) {
      toast.success(`${doneCount.value} ${doneCount.value === 1 ? 'entry' : 'entries'} categorised`)
      await finance.changed()
    }
  } catch (e) {
    error.value = e instanceof ApiError && e.kind === 'conflict' ? 'This entry changed elsewhere. Reloading the list.' : e instanceof ApiError ? e.message : 'Could not save.'
    if (e instanceof ApiError && e.kind === 'conflict') await load()
  } finally {
    saving.value = false
  }
}
function skip() {
  index.value++
}
</script>

<template>
  <div class="pb-2">
    <p v-if="loading" class="py-10 text-center text-sm text-ink-muted">Loading…</p>
    <EmptyState v-else-if="!current" icon="check" title="All categorised" :message="doneCount ? 'Future payments to the same payees are categorised automatically.' : 'Entries from bank alerts appear here until you choose a category.'">
      <button type="button" class="h-10 rounded-full bg-brand-solid px-5 text-sm font-semibold text-white" @click="emit('done')">Done</button>
    </EmptyState>
    <template v-else>
      <p class="mb-3 text-center text-[13px] text-ink-muted">{{ index + 1 }} of {{ queue.length }}</p>
      <div class="mb-4 rounded-card bg-ink/[0.03] p-4 text-center ring-1 ring-line/60">
        <p class="text-[15px] font-semibold text-ink">{{ current.title }}</p>
        <Money
          :value="current.transaction_type === 'Income' ? current.amount : -current.amount"
          :sign="current.transaction_type === 'Income' ? 'always' : 'auto'"
          :tone="current.transaction_type === 'Income' ? 'income' : 'expense'"
          size="xl"
          class="mt-1 block"
        />
        <p class="mt-1 text-[13px] text-ink-muted">
          {{ dayLabel(current.transaction_date) }}, {{ current.account_name }}<template v-if="current.bank_reference">, ref {{ current.bank_reference }}</template>
        </p>
      </div>
      <h3 class="mb-2 text-sm font-medium text-ink">{{ current.transaction_type === 'Income' ? 'What was this income?' : 'What was this for?' }}</h3>
      <div role="radiogroup" aria-label="Category" class="grid grid-cols-4 gap-1.5 sm:grid-cols-5">
        <button
          v-for="c in options"
          :key="c.name"
          type="button"
          role="radio"
          aria-checked="false"
          class="flex flex-col items-center gap-1 rounded-tile px-1 py-2 text-center hover:bg-ink/[0.04] disabled:opacity-50"
          :disabled="saving"
          @click="choose(c.name)"
        >
          <CategoryIcon :icon="c.icon" :color="c.color" size="sm" />
          <span class="line-clamp-2 text-[11.5px] leading-tight text-ink">{{ c.category_name }}</span>
        </button>
      </div>
      <p v-if="error" role="alert" class="mt-3 text-sm text-expense">{{ error }}</p>
      <div class="mt-4 flex justify-between">
        <button type="button" class="inline-flex h-10 items-center gap-1 rounded-full px-4 text-sm font-medium text-ink-muted hover:bg-ink/[0.05]" @click="skip">
          Skip <AppIcon name="chevron-right" class="size-4" />
        </button>
        <button type="button" class="h-10 rounded-full px-4 text-sm font-medium text-ink ring-1 ring-line" @click="emit('done')">Finish later</button>
      </div>
    </template>
  </div>
</template>
