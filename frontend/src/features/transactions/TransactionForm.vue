<script setup lang="ts">
/**
 * Quick Add / edit transaction form.
 *
 * Speed path (3–5 s): type is preselected, the amount field is focused,
 * the most-used categories come first, the last-used account and today's
 * date are preselected, and Enter saves.
 *
 * Duplicate protection: one client transaction ID per form session. The
 * server treats a repeated ID as the same transaction, so double taps,
 * retries after a timeout and (later) offline replays can never duplicate.
 */
import { computed, onMounted, ref, watch } from 'vue'
import { toast } from 'frappe-ui'
import AmountInput from '@/components/ui/AmountInput.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import CategoryIcon from '@/components/ui/CategoryIcon.vue'
import Money from '@/components/ui/Money.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import CategoryInlineForm from '@/features/categories/CategoryInlineForm.vue'
import { useIsDesktop } from '@/composables/useBreakpoint'
import { ApiError } from '@/services/api'
import { attachmentsApi, MAX_RECEIPT_MB, transactionsApi } from '@/services/finance'
import { useFinanceStore } from '@/stores/finance'
import { useSyncStore } from '@/stores/sync'
import type { Category, TransactionInput, TransactionRowData, TransactionType } from '@/types/finance'
import { toISO, todayISO } from '@/utils/date'
import { isUncategorised } from '@/utils/categories'
import { uuid } from '@/utils/id'
import { formatMoney, parseAmount } from '@/utils/money'

const props = defineProps<{
  editing?: TransactionRowData | null
  defaultType?: TransactionType
  defaultAccount?: string | null
}>()
const emit = defineEmits<{ saved: [txn: TransactionRowData]; cancel: [] }>()

const finance = useFinanceStore()
const sync = useSyncStore()
const isDesktop = useIsDesktop()
const isEdit = computed(() => !!props.editing)

// ----- form state -------------------------------------------------------------
const type = ref<TransactionType>(props.editing?.transaction_type ?? props.defaultType ?? 'Expense')
const amount = ref(props.editing ? String(props.editing.amount) : '')
const category = ref<string | null>(props.editing?.category ?? null)
const account = ref<string | null>(props.editing?.account ?? null)
const toAccount = ref<string | null>(props.editing?.to_account ?? null)
const date = ref(props.editing?.transaction_date ?? todayISO())
const title = ref(props.editing && props.editing.title !== props.editing.category_name ? props.editing.title : '')
const notes = ref(props.editing?.notes ?? '')
const isRefund = ref(!!props.editing?.is_refund)
const showMore = ref(!!(props.editing?.notes || props.editing?.is_refund))
const addingCategory = ref(false)
const receiptFiles = ref<File[]>([])
const receiptInput = ref<HTMLInputElement>()

const clientTxnId = uuid()
const saving = ref(false)
const errors = ref<Record<string, string>>({})
const serverError = ref<string | null>(null)
const conflict = ref(false)
const suggested = ref<string[]>([])

const typeOptions = [
  { value: 'Expense' as const, label: 'Expense', tone: 'expense' as const },
  { value: 'Income' as const, label: 'Income', tone: 'income' as const },
  { value: 'Transfer' as const, label: 'Transfer', tone: 'accent' as const },
]

// ----- reference data ------------------------------------------------------------
const accounts = computed(() => finance.accounts.filter((a) => !a.is_archived || a.name === account.value || a.name === toAccount.value))

function pickDefaultAccount() {
  if (account.value) return
  const candidates = [props.defaultAccount, finance.defaultAccount, finance.lastUsedAccount, accounts.value[0]?.name]
  account.value = candidates.find((n) => n && accounts.value.some((a) => a.name === n)) ?? null
}

/** Top-level categories, most recently/frequently used first. */
const categoryGrid = computed(() => {
  if (type.value === 'Transfer') return []
  // "Uncategorised" is only for automatic entries; manual entries always get a real category.
  const tree = finance.categoryTree(type.value).filter((c) => !isUncategorised(c))
  const rank = new Map(suggested.value.map((n, i) => [n, i]))
  const score = (c: { name: string; children: Category[] }) =>
    Math.min(rank.get(c.name) ?? 999, ...c.children.map((ch) => rank.get(ch.name) ?? 999))
  return [...tree].sort((a, b) => score(a) - score(b) || a.sort_order - b.sort_order)
})

const selectedParent = computed(() => {
  const c = category.value ? finance.categoryMap.get(category.value) : null
  return c ? (c.parent_category ?? c.name) : null
})
const subcategories = computed(() => categoryGrid.value.find((p) => p.name === selectedParent.value)?.children ?? [])

async function loadSuggestions() {
  if (type.value === 'Transfer') return
  try {
    const s = await transactionsApi.suggested(type.value)
    suggested.value = [...new Set([...s.recent.slice(0, 4), ...s.frequent, ...s.recent])]
  } catch {
    suggested.value = [] // ordering hint only; the grid still works
  }
}

onMounted(async () => {
  await finance.load()
  pickDefaultAccount()
  loadSuggestions()
})

watch(type, (t) => {
  errors.value = {}
  // A category of the other type is never valid; clear it.
  const c = category.value ? finance.categoryMap.get(category.value) : null
  if (!c || c.category_type !== t) category.value = null
  if (t !== 'Expense') isRefund.value = false
  addingCategory.value = false
  loadSuggestions()
})

// ----- dates -------------------------------------------------------------------
const yesterday = computed(() => {
  const d = new Date()
  d.setDate(d.getDate() - 1)
  return toISO(d)
})

// ----- validation & save -------------------------------------------------------
const tone = computed(() => (type.value === 'Income' ? 'income' : type.value === 'Transfer' ? 'brand' : 'expense'))

function validate(): TransactionInput | null {
  const e: Record<string, string> = {}
  const value = parseAmount(amount.value)
  if (value === null) e.amount = amount.value ? 'Enter an amount greater than zero.' : 'Enter an amount.'
  if (!account.value) e.account = 'Choose an account.'
  if (type.value === 'Transfer') {
    if (!toAccount.value) e.to_account = 'Choose where the money goes.'
    else if (toAccount.value === account.value) e.to_account = 'Choose a different account.'
  } else if (!category.value) {
    e.category = 'Choose a category.'
  }
  if (!date.value) e.date = 'Choose a date.'
  errors.value = e
  if (Object.keys(e).length) return null
  return {
    transaction_type: type.value,
    amount: value!,
    transaction_date: date.value,
    account: account.value!,
    to_account: type.value === 'Transfer' ? toAccount.value : null,
    category: type.value === 'Transfer' ? null : category.value,
    title: title.value.trim() || null,
    notes: notes.value.trim() || null,
    is_refund: type.value === 'Expense' && isRefund.value ? 1 : 0,
  }
}

/**
 * Keep the change on this device for later sync. The same client ID is used,
 * so if the original request did reach the server, sync reports a duplicate
 * instead of creating a second transaction.
 */
async function saveOffline(data: TransactionInput): Promise<boolean> {
  const ok = isEdit.value
    ? await sync.enqueue('update', { name: props.editing!.name, data, expected_modified: props.editing!.modified })
    : await sync.enqueue('create', { id: clientTxnId, data })
  if (!ok) return false
  toast.success(isEdit.value ? 'Saved on this device. It will sync when you are online.' : `${data.transaction_type} saved on this device. It will sync when you are online.`)
  if (!isEdit.value) finance.lastUsedAccount = data.account
  emit('saved', { ...(props.editing ?? {}), ...data, name: props.editing?.name ?? clientTxnId, pending: true } as TransactionRowData)
  return true
}

async function save() {
  if (saving.value) return // prevents double submit
  serverError.value = null
  const data = validate()
  if (!data) return
  saving.value = true
  // Offline, or editing an entry that is itself still waiting to sync: queue it.
  if (!sync.online || props.editing?.pending) {
    const queued = await saveOffline(data)
    saving.value = false
    if (!queued) serverError.value = 'You are offline and this browser cannot store changes. Try again when you are back online.'
    return
  }
  try {
    let txn: TransactionRowData
    if (isEdit.value) {
      txn = (await transactionsApi.update(props.editing!.name, data, conflict.value ? undefined : props.editing!.modified)).transaction
      toast.success(`${data.transaction_type} updated`)
    } else {
      const res = await transactionsApi.create(data, clientTxnId)
      txn = res.transaction
      finance.lastUsedAccount = txn.account
      toast.success(`${data.transaction_type} of ${formatMoney(data.amount)} saved`)
      await uploadReceipts(txn.name)
    }
    await finance.changed()
    emit('saved', txn)
  } catch (e) {
    if (e instanceof ApiError && e.kind === 'conflict') {
      conflict.value = true
      serverError.value = `${e.message} Saving again will replace the other version with yours.`
    } else if (e instanceof ApiError && e.kind === 'network') {
      sync.online = navigator.onLine
      if (!(await saveOffline(data))) serverError.value = 'No connection. Your entry is still here; try again when you are back online.'
    } else if (e instanceof ApiError) {
      serverError.value =
        e.kind === 'auth'
            ? 'Your session has expired. Log in again, then save.'
            : e.message
    } else {
      serverError.value = 'Something went wrong while saving. Try again.'
    }
  } finally {
    saving.value = false
  }
}

function onReceipts(e: Event) {
  const files = [...((e.target as HTMLInputElement).files ?? [])]
  ;(e.target as HTMLInputElement).value = ''
  const tooBig = files.filter((f) => f.size > MAX_RECEIPT_MB * 1024 * 1024)
  if (tooBig.length) toast.error(`${tooBig[0].name} is larger than ${MAX_RECEIPT_MB} MB.`)
  receiptFiles.value = [...receiptFiles.value, ...files.filter((f) => !tooBig.includes(f))].slice(0, 5)
}

/** The transaction is already saved; a failed upload never loses it. */
async function uploadReceipts(transaction: string) {
  for (const f of receiptFiles.value) {
    try {
      await attachmentsApi.upload(transaction, f)
    } catch (e) {
      toast.error(`Saved, but ${f.name} didn't upload${e instanceof ApiError ? `: ${e.message}` : ''}. Add it from the transaction's details.`)
    }
  }
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
    e.preventDefault()
    save()
  }
}

function onCategoryCreated(c: Category) {
  addingCategory.value = false
  category.value = c.name
  errors.value.category = ''
}

function selectCategory(name: string) {
  category.value = name
  if (errors.value.category) errors.value.category = ''
}
</script>

<template>
  <form class="space-y-5 pt-1" novalidate @submit.prevent="save" @keydown="onKeydown">
    <SegmentedControl v-model="type" :options="typeOptions" label="Transaction type" />

    <AmountInput
      v-model="amount"
      :tone="tone"
      :autofocus="!isEdit"
      :error="errors.amount"
      class="py-2"
      @keydown.enter.prevent="save"
    />

    <!-- Category -->
    <section v-if="type !== 'Transfer'" aria-labelledby="cat-label">
      <div class="mb-2 flex items-center justify-between">
        <h3 id="cat-label" class="text-sm font-medium text-ink">Category</h3>
        <button
          v-if="!addingCategory"
          type="button"
          class="inline-flex items-center gap-1 text-sm font-medium text-brand-ink hover:underline"
          @click="addingCategory = true"
        >
          <AppIcon name="plus" class="size-4" /> New
        </button>
      </div>
      <CategoryInlineForm v-if="addingCategory" :type="type as 'Expense' | 'Income'" @created="onCategoryCreated" @cancel="addingCategory = false" />
      <div v-else role="radiogroup" aria-labelledby="cat-label" class="grid grid-cols-4 gap-1.5 sm:grid-cols-6">
        <button
          v-for="c in categoryGrid"
          :key="c.name"
          type="button"
          role="radio"
          :aria-checked="selectedParent === c.name"
          class="flex flex-col items-center gap-1 rounded-tile px-1 py-2 text-center transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand"
          :class="selectedParent === c.name ? 'bg-ink/[0.06] ring-2 ring-inset' : 'hover:bg-ink/[0.04]'"
          :style="selectedParent === c.name ? { '--tw-ring-color': c.color } : undefined"
          @click="selectCategory(c.name)"
        >
          <CategoryIcon :icon="c.icon" :color="c.color" size="sm" />
          <span class="line-clamp-2 text-[11.5px] leading-tight text-ink">{{ c.category_name }}</span>
        </button>
      </div>
      <div v-if="!addingCategory && subcategories.length" class="mt-2 flex flex-wrap gap-1.5" role="radiogroup" aria-label="Subcategory">
        <button
          v-for="s in [{ name: selectedParent!, category_name: 'General' }, ...subcategories]"
          :key="s.name"
          type="button"
          role="radio"
          :aria-checked="category === s.name"
          class="h-8 rounded-full px-3 text-[13px] font-medium ring-1"
          :class="category === s.name ? 'bg-ink text-canvas ring-ink' : 'text-ink-muted ring-line hover:text-ink'"
          @click="selectCategory(s.name)"
        >
          {{ s.category_name }}
        </button>
      </div>
      <p v-if="errors.category" role="alert" class="mt-2 text-sm text-expense">{{ errors.category }}</p>
    </section>

    <!-- Accounts -->
    <section v-for="field in type === 'Transfer' ? (['account', 'to_account'] as const) : (['account'] as const)" :key="field">
      <h3 class="mb-2 text-sm font-medium text-ink">
        {{ type === 'Transfer' ? (field === 'account' ? 'From' : 'To') : type === 'Income' ? 'Received in' : 'Paid from' }}
      </h3>
      <div class="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1" role="radiogroup" :aria-label="field === 'account' ? 'Account' : 'Destination account'">
        <button
          v-for="a in accounts"
          :key="a.name"
          type="button"
          role="radio"
          :aria-checked="(field === 'account' ? account : toAccount) === a.name"
          :disabled="field === 'to_account' && a.name === account"
          class="flex shrink-0 items-center gap-2 rounded-tile py-2 pl-2 pr-3 text-left ring-1 transition-colors disabled:opacity-40"
          :class="(field === 'account' ? account : toAccount) === a.name ? 'bg-brand-soft ring-2 ring-brand' : 'ring-line hover:bg-ink/[0.03]'"
          @click="field === 'account' ? (account = a.name) : (toAccount = a.name)"
        >
          <CategoryIcon :icon="a.icon" :color="a.color" size="sm" />
          <span>
            <span class="block text-[13px] font-medium leading-tight text-ink">{{ a.account_name }}</span>
            <Money :value="a.balance" size="sm" tone="muted" class="block text-xs" />
          </span>
        </button>
      </div>
      <p v-if="errors[field]" role="alert" class="mt-1 text-sm text-expense">{{ errors[field] }}</p>
    </section>

    <!-- Date -->
    <section>
      <h3 class="mb-2 text-sm font-medium text-ink">Date</h3>
      <div class="flex flex-wrap items-center gap-2">
        <button
          v-for="opt in [{ v: todayISO(), l: 'Today' }, { v: yesterday, l: 'Yesterday' }]"
          :key="opt.l"
          type="button"
          class="h-9 rounded-full px-4 text-sm font-medium ring-1"
          :class="date === opt.v ? 'bg-ink text-canvas ring-ink' : 'text-ink-muted ring-line hover:text-ink'"
          :aria-pressed="date === opt.v"
          @click="date = opt.v"
        >
          {{ opt.l }}
        </button>
        <label class="relative">
          <span class="sr-only">Pick a date</span>
          <input
            v-model="date"
            type="date"
            :max="toISO(new Date(new Date().getFullYear() + 5, 0, 1))"
            class="h-9 rounded-full border-0 bg-transparent px-3 text-sm text-ink ring-1 ring-line focus:ring-2 focus:ring-brand"
          />
        </label>
      </div>
      <p v-if="errors.date" role="alert" class="mt-1 text-sm text-expense">{{ errors.date }}</p>
    </section>

    <!-- Description -->
    <label class="block">
      <span class="mb-2 block text-sm font-medium text-ink">Description <span class="font-normal text-ink-faint">(optional)</span></span>
      <input
        v-model="title"
        maxlength="140"
        :placeholder="type === 'Transfer' ? 'e.g. Credit card bill' : 'e.g. Dinner with friends'"
        class="h-11 w-full rounded-tile border-0 bg-card px-3 text-[15px] text-ink ring-1 ring-line placeholder:text-ink-faint focus:ring-2 focus:ring-brand"
        @keydown.enter.prevent="save"
      />
    </label>

    <!-- Receipt (new transactions; edits use the details sheet) -->
    <section v-if="!isEdit" aria-labelledby="receipt-label">
      <div class="flex items-center justify-between">
        <h3 id="receipt-label" class="text-sm font-medium text-ink">Receipt <span class="font-normal text-ink-faint">(optional)</span></h3>
        <button
          v-if="sync.online"
          type="button"
          class="inline-flex items-center gap-1 text-sm font-medium text-brand-ink hover:underline"
          @click="receiptInput?.click()"
        >
          <AppIcon name="paperclip" class="size-4" /> {{ receiptFiles.length ? 'Add another' : 'Attach photo or PDF' }}
        </button>
        <span v-else class="text-[13px] text-ink-muted">Available when online</span>
        <input ref="receiptInput" type="file" accept="image/*,application/pdf" multiple class="hidden" @change="onReceipts" />
      </div>
      <ul v-if="receiptFiles.length" class="mt-2 flex flex-wrap gap-1.5">
        <li v-for="(f, i) in receiptFiles" :key="f.name + i" class="inline-flex h-8 max-w-full items-center gap-1.5 rounded-full bg-ink/[0.05] pl-3 pr-1 text-[13px] text-ink">
          <span class="truncate">{{ f.name }}</span>
          <button type="button" class="inline-flex size-6 items-center justify-center rounded-full hover:bg-ink/10" :aria-label="`Remove ${f.name}`" @click="receiptFiles.splice(i, 1)">
            <AppIcon name="x" class="size-3.5" />
          </button>
        </li>
      </ul>
    </section>

    <div>
      <button
        v-if="!showMore"
        type="button"
        class="inline-flex items-center gap-1 text-sm font-medium text-ink-muted hover:text-ink"
        @click="showMore = true"
      >
        <AppIcon name="chevron-down" class="size-4" /> Notes{{ type === 'Expense' ? ' and refund' : '' }}
      </button>
      <div v-else class="space-y-3">
        <label class="block">
          <span class="mb-2 block text-sm font-medium text-ink">Notes</span>
          <textarea
            v-model="notes"
            rows="2"
            maxlength="2000"
            class="w-full rounded-tile border-0 bg-card px-3 py-2 text-[15px] text-ink ring-1 ring-line focus:ring-2 focus:ring-brand"
          />
        </label>
        <label v-if="type === 'Expense'" class="flex items-start gap-3 text-sm text-ink">
          <input v-model="isRefund" type="checkbox" class="mt-0.5 size-4 rounded text-brand-solid focus:ring-brand" />
          <span>
            This is a refund
            <span class="block text-ink-muted">Money returned for an earlier purchase. It reduces your spending.</span>
          </span>
        </label>
      </div>
    </div>

    <div v-if="serverError" role="alert" class="flex gap-2 rounded-tile bg-expense-soft/60 p-3 text-sm text-ink">
      <AppIcon name="circle-alert" class="mt-0.5 size-4 shrink-0 text-expense" />
      {{ serverError }}
    </div>

    <div class="sticky bottom-0 -mx-1 flex gap-2 bg-gradient-to-t from-card via-card to-card/0 px-1 pb-1 pt-3">
      <button
        v-if="isDesktop"
        type="button"
        class="h-12 rounded-full px-5 font-medium text-ink-muted hover:bg-ink/[0.05]"
        @click="emit('cancel')"
      >
        Cancel
      </button>
      <button
        type="submit"
        class="flex h-12 flex-1 items-center justify-center gap-2 rounded-full font-semibold text-white transition-opacity disabled:opacity-70"
        :class="{ expense: 'bg-expense-solid', income: 'bg-income-solid', brand: 'bg-accent-solid' }[tone]"
        :disabled="saving"
        :aria-busy="saving"
      >
        <AppIcon :name="saving ? 'refresh-cw' : 'check'" class="size-5" :class="{ 'animate-spin': saving }" />
        {{ saving ? 'Saving…' : isEdit ? 'Save changes' : `Save ${type.toLowerCase()}` }}
        <kbd v-if="isDesktop && !saving" class="ml-1 rounded bg-white/15 px-1.5 text-[11px] font-medium">Ctrl ↵</kbd>
      </button>
    </div>
  </form>
</template>
