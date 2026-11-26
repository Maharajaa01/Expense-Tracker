<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { toast } from 'frappe-ui'
import AmountInput from '@/components/ui/AmountInput.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import SelectField from '@/components/ui/SelectField.vue'
import { ApiError } from '@/services/api'
import { recurringApi } from '@/services/finance'
import { useFinanceStore } from '@/stores/finance'
import type { Frequency, Recurring, TransactionType } from '@/types/finance'
import { todayISO } from '@/utils/date'
import { parseAmount } from '@/utils/money'

const props = defineProps<{ recurring?: Recurring | null }>()
const emit = defineEmits<{ saved: [r: Recurring]; cancel: [] }>()
const finance = useFinanceStore()
const r = props.recurring
onMounted(() => finance.load())

const title = ref(r?.title ?? '')
const type = ref<TransactionType>(r?.transaction_type ?? 'Expense')
const amount = ref(r ? String(r.amount) : '')
const category = ref(r?.category ?? '')
const account = ref(r?.account ?? finance.defaultAccount ?? finance.lastUsedAccount ?? '')
const toAccount = ref(r?.to_account ?? '')
const frequency = ref<Frequency>(r?.frequency ?? 'Monthly')
const interval = ref(String(r?.interval ?? 1))
const unit = ref<'Days' | 'Weeks' | 'Months'>(r?.custom_unit ?? 'Days')
const startDate = ref(r?.start_date ?? todayISO())
const endDate = ref(r?.end_date ?? '')
const autoPost = ref(r ? !!r.auto_post : true)
const remind = ref(String(r?.remind_days_before ?? 2))
const notes = ref(r?.notes ?? '')
const saving = ref(false)
const error = ref<string | null>(null)
const fieldErrors = ref<Record<string, string>>({})

watch(type, () => (category.value = ''))
const categoryOptions = computed(() => {
  if (type.value === 'Transfer') return []
  const out: { value: string; label: string }[] = []
  for (const p of finance.categoryTree(type.value)) {
    out.push({ value: p.name, label: p.category_name })
    for (const c of p.children) out.push({ value: c.name, label: `${p.category_name} › ${c.category_name}` })
  }
  return out
})
const accountOptions = computed(() => finance.activeAccounts.map((a) => ({ value: a.name, label: a.account_name })))
const frequencyOptions = [
  { value: 'Daily', label: 'Daily' }, { value: 'Weekly', label: 'Weekly' }, { value: 'Monthly', label: 'Monthly' },
  { value: 'Quarterly', label: 'Quarterly' }, { value: 'Yearly', label: 'Yearly' }, { value: 'Custom', label: 'Custom interval' },
]
const unitWord = computed(() => {
  const n = Number(interval.value) || 1
  const base = frequency.value === 'Custom' ? unit.value.toLowerCase().replace(/s$/, '')
    : { Daily: 'day', Weekly: 'week', Monthly: 'month', Quarterly: 'quarter', Yearly: 'year' }[frequency.value]
  return n === 1 ? base : `${base}s`
})

async function save() {
  if (saving.value) return
  const e: Record<string, string> = {}
  const value = parseAmount(amount.value)
  if (!title.value.trim()) e.title = 'Give it a name, like Rent or Netflix.'
  if (value === null) e.amount = 'Enter the amount.'
  if (!account.value) e.account = 'Choose an account.'
  if (type.value === 'Transfer' && (!toAccount.value || toAccount.value === account.value)) e.to_account = 'Choose a different account to transfer to.'
  if (type.value !== 'Transfer' && !category.value) e.category = 'Choose a category.'
  fieldErrors.value = e
  if (Object.keys(e).length) return
  saving.value = true
  error.value = null
  try {
    const data: Partial<Recurring> = {
      title: title.value.trim(), transaction_type: type.value, amount: value!,
      category: type.value === 'Transfer' ? null : category.value,
      account: account.value, to_account: type.value === 'Transfer' ? toAccount.value : null,
      frequency: frequency.value, interval: Math.max(Number(interval.value) || 1, 1),
      custom_unit: frequency.value === 'Custom' ? unit.value : null,
      start_date: startDate.value, end_date: endDate.value || null,
      auto_post: autoPost.value ? 1 : 0, remind_days_before: Math.max(Number(remind.value) || 0, 0),
      notes: notes.value.trim() || null,
    }
    const saved = r ? await recurringApi.update(r.name, data) : await recurringApi.create(data)
    toast.success(r ? 'Recurring payment updated' : 'Recurring payment added')
    finance.dataVersion++
    emit('saved', saved)
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : 'Could not save.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <form class="space-y-5 pt-1" novalidate @submit.prevent="save">
    <SegmentedControl v-model="type" label="Type" :options="[{ value: 'Expense', label: 'Expense', tone: 'expense' }, { value: 'Income', label: 'Income', tone: 'income' }, { value: 'Transfer', label: 'Transfer', tone: 'accent' }]" />
    <label class="block">
      <span class="mb-1.5 block text-sm font-medium text-ink">Name</span>
      <input v-model="title" maxlength="140" :placeholder="type === 'Income' ? 'e.g. Salary' : 'e.g. Rent, Netflix, Electricity'" class="h-11 w-full rounded-tile border-0 bg-card px-3 text-[15px] text-ink ring-1 ring-line focus:ring-2 focus:ring-brand" />
      <span v-if="fieldErrors.title" role="alert" class="mt-1 block text-sm text-expense">{{ fieldErrors.title }}</span>
    </label>
    <AmountInput v-model="amount" :tone="type === 'Income' ? 'income' : type === 'Transfer' ? 'brand' : 'expense'" :error="fieldErrors.amount" class="py-1" />

    <div class="grid gap-3 sm:grid-cols-2">
      <div v-if="type !== 'Transfer'">
        <SelectField v-model="category" label="Category" :options="categoryOptions" placeholder="Choose a category" />
        <span v-if="fieldErrors.category" role="alert" class="mt-1 block text-sm text-expense">{{ fieldErrors.category }}</span>
      </div>
      <div>
        <SelectField v-model="account" :label="type === 'Transfer' ? 'From' : type === 'Income' ? 'Received in' : 'Paid from'" :options="accountOptions" placeholder="Choose an account" />
        <span v-if="fieldErrors.account" role="alert" class="mt-1 block text-sm text-expense">{{ fieldErrors.account }}</span>
      </div>
      <div v-if="type === 'Transfer'">
        <SelectField v-model="toAccount" label="To" :options="accountOptions" placeholder="Choose an account" />
        <span v-if="fieldErrors.to_account" role="alert" class="mt-1 block text-sm text-expense">{{ fieldErrors.to_account }}</span>
      </div>
    </div>

    <fieldset class="rounded-tile bg-ink/[0.03] p-4 ring-1 ring-line/60">
      <legend class="sr-only">Schedule</legend>
      <div class="grid gap-3 sm:grid-cols-2">
        <SelectField v-model="frequency" label="Repeats" :options="frequencyOptions" />
        <div class="flex items-end gap-2">
          <label class="block flex-1 text-sm">
            <span class="mb-1.5 block font-medium text-ink">Every</span>
            <input v-model="interval" type="number" min="1" max="365" inputmode="numeric" class="h-10 w-full rounded-[10px] border-0 bg-card px-3 text-ink ring-1 ring-line focus:ring-2 focus:ring-brand" />
          </label>
          <SelectField v-if="frequency === 'Custom'" v-model="unit" label="Unit" hide-label :options="[{ value: 'Days', label: 'days' }, { value: 'Weeks', label: 'weeks' }, { value: 'Months', label: 'months' }]" class="flex-1" />
          <span v-else class="pb-2.5 text-sm text-ink-muted">{{ unitWord }}</span>
        </div>
        <label class="block text-sm">
          <span class="mb-1.5 block font-medium text-ink">First payment</span>
          <input v-model="startDate" type="date" class="h-10 w-full rounded-[10px] border-0 bg-card px-3 text-ink ring-1 ring-line focus:ring-2 focus:ring-brand" />
        </label>
        <label class="block text-sm">
          <span class="mb-1.5 block font-medium text-ink">Ends <span class="font-normal text-ink-faint">(optional)</span></span>
          <input v-model="endDate" type="date" :min="startDate" class="h-10 w-full rounded-[10px] border-0 bg-card px-3 text-ink ring-1 ring-line focus:ring-2 focus:ring-brand" />
        </label>
      </div>
      <p class="mt-3 text-[13px] text-ink-muted">Past dates are not filled in automatically; payments start from today onwards.</p>
    </fieldset>

    <fieldset class="space-y-2">
      <legend class="mb-1 text-sm font-medium text-ink">When it's due</legend>
      <label class="flex items-start gap-3 text-sm text-ink">
        <input v-model="autoPost" type="radio" :value="true" class="mt-0.5 size-4 text-brand-solid focus:ring-brand" />
        <span>Add it automatically<span class="block text-ink-muted">Good for fixed amounts like rent, EMIs and subscriptions.</span></span>
      </label>
      <label class="flex items-start gap-3 text-sm text-ink">
        <input v-model="autoPost" type="radio" :value="false" class="mt-0.5 size-4 text-brand-solid focus:ring-brand" />
        <span>Remind me and I'll confirm<span class="block text-ink-muted">Good for bills that change, like electricity.</span></span>
      </label>
    </fieldset>
    <label class="flex items-center gap-2 text-sm text-ink">
      Remind me
      <input v-model="remind" type="number" min="0" max="30" inputmode="numeric" class="h-9 w-16 rounded-[10px] border-0 bg-card px-2 text-center text-ink ring-1 ring-line focus:ring-2 focus:ring-brand" />
      days before
    </label>

    <p v-if="error" role="alert" class="rounded-tile bg-expense-soft/60 p-3 text-sm text-ink">{{ error }}</p>
    <div class="flex gap-2">
      <button type="button" class="h-12 rounded-full px-5 font-medium text-ink-muted hover:bg-ink/[0.05]" @click="emit('cancel')">Cancel</button>
      <button type="submit" class="flex h-12 flex-1 items-center justify-center gap-2 rounded-full bg-brand-solid font-semibold text-white disabled:opacity-70" :disabled="saving">
        <AppIcon v-if="saving" name="refresh-cw" class="size-5 animate-spin" />
        {{ r ? 'Save changes' : 'Add recurring payment' }}
      </button>
    </div>
  </form>
</template>
