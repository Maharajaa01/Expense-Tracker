<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { toast } from 'frappe-ui'
import AmountInput from '@/components/ui/AmountInput.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import SelectField from '@/components/ui/SelectField.vue'
import { ApiError } from '@/services/api'
import { budgetsApi } from '@/services/finance'
import { useFinanceStore } from '@/stores/finance'
import type { Budget } from '@/types/finance'
import { toISO } from '@/utils/date'
import { parseAmount } from '@/utils/money'

const props = defineProps<{ budget?: Budget | null }>()
const emit = defineEmits<{ saved: [b: Budget]; cancel: [] }>()
const finance = useFinanceStore()
const b = props.budget
const firstOfMonth = toISO(new Date(new Date().getFullYear(), new Date().getMonth(), 1))

const category = ref(b?.category ?? '')
const name = ref(b?.budget_name ?? '')
const nameTouched = ref(!!b)
const amount = ref(b?.progress ? String(b.progress.amount) : b?.amount ? String(b.amount) : '')
const periodType = ref<'Monthly' | 'Custom'>(b?.period_type ?? 'Monthly')
const startDate = ref(b?.start_date ?? firstOfMonth)
const endDate = ref(b?.end_date ?? '')
const carry = ref(!!b?.carry_forward)
const alert50 = ref(b ? !!b.alert_50 : true)
const alert80 = ref(b ? !!b.alert_80 : true)
const alert100 = ref(b ? !!b.alert_100 : true)
const saving = ref(false)
const error = ref<string | null>(null)
const amountError = ref<string | null>(null)

const categoryOptions = computed(() => {
  const out: { value: string; label: string }[] = []
  for (const p of finance.categoryTree('Expense')) {
    out.push({ value: p.name, label: p.category_name })
    for (const c of p.children) out.push({ value: c.name, label: `${p.category_name} › ${c.category_name}` })
  }
  return out
})
// Name follows the category until the user types their own.
watch(category, (c) => {
  if (nameTouched.value) return
  name.value = c ? finance.categoryMap.get(c)?.category_name ?? '' : 'Monthly spending'
}, { immediate: !b })

async function save() {
  if (saving.value) return
  const value = parseAmount(amount.value)
  amountError.value = value === null ? 'Enter the amount you plan to spend.' : null
  if (value === null) return
  if (periodType.value === 'Custom' && (!endDate.value || endDate.value < startDate.value)) {
    error.value = 'Choose an end date on or after the start date.'
    return
  }
  saving.value = true
  error.value = null
  try {
    const data = {
      budget_name: name.value.trim() || 'Budget',
      category: category.value || null,
      amount: value,
      period_type: periodType.value,
      start_date: startDate.value,
      end_date: periodType.value === 'Custom' ? endDate.value : null,
      carry_forward: (periodType.value === 'Monthly' && carry.value ? 1 : 0) as 0 | 1,
      is_active: (b ? b.is_active : 1) as 0 | 1,
      alert_50: (alert50.value ? 1 : 0) as 0 | 1,
      alert_80: (alert80.value ? 1 : 0) as 0 | 1,
      alert_100: (alert100.value ? 1 : 0) as 0 | 1,
    }
    const saved = b ? await budgetsApi.update(b.name, data) : await budgetsApi.create(data)
    toast.success(b ? 'Budget updated' : 'Budget created')
    finance.dataVersion++
    emit('saved', saved)
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Could not save the budget.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <form class="space-y-5 pt-1" novalidate @submit.prevent="save">
    <SelectField v-model="category" label="What is this budget for?" :options="categoryOptions" placeholder="All spending (overall budget)" />

    <label class="block">
      <span class="mb-1.5 block text-sm font-medium text-ink">Name</span>
      <input v-model="name" maxlength="100" class="h-11 w-full rounded-tile border-0 bg-card px-3 text-[15px] text-ink ring-1 ring-line focus:ring-2 focus:ring-brand" @input="nameTouched = true" />
    </label>

    <section class="rounded-tile bg-ink/[0.03] p-4 ring-1 ring-line/60">
      <h3 class="text-center text-sm font-medium text-ink">{{ periodType === 'Monthly' ? 'Spending limit per month' : 'Spending limit for the period' }}</h3>
      <AmountInput v-model="amount" tone="brand" label="Budget amount" :error="amountError" class="py-2" />
    </section>

    <SegmentedControl v-model="periodType" label="Budget period" :options="[{ value: 'Monthly', label: 'Every month' }, { value: 'Custom', label: 'Custom dates' }]" />

    <div class="grid grid-cols-2 gap-3">
      <label class="block text-sm">
        <span class="mb-1.5 block font-medium text-ink">{{ periodType === 'Monthly' ? 'Starting' : 'From' }}</span>
        <input v-model="startDate" type="date" class="h-10 w-full rounded-[10px] border-0 bg-card px-3 text-ink ring-1 ring-line focus:ring-2 focus:ring-brand" />
      </label>
      <label v-if="periodType === 'Custom'" class="block text-sm">
        <span class="mb-1.5 block font-medium text-ink">To</span>
        <input v-model="endDate" type="date" :min="startDate" class="h-10 w-full rounded-[10px] border-0 bg-card px-3 text-ink ring-1 ring-line focus:ring-2 focus:ring-brand" />
      </label>
    </div>

    <label v-if="periodType === 'Monthly'" class="flex items-start gap-3 text-sm text-ink">
      <input v-model="carry" type="checkbox" class="mt-0.5 size-4 rounded text-brand-solid focus:ring-brand" />
      <span>Carry over what's left<span class="block text-ink-muted">Unspent money from last month is added to this month. Overspending is never carried.</span></span>
    </label>

    <fieldset>
      <legend class="mb-2 text-sm font-medium text-ink">Alert me when I've used</legend>
      <div class="flex flex-wrap gap-2">
        <label class="inline-flex h-9 cursor-pointer items-center gap-2 rounded-full px-3 text-sm ring-1 ring-line">
          <input v-model="alert50" type="checkbox" class="size-4 rounded text-brand-solid focus:ring-brand" /> 50%
        </label>
        <label class="inline-flex h-9 cursor-pointer items-center gap-2 rounded-full px-3 text-sm ring-1 ring-line">
          <input v-model="alert80" type="checkbox" class="size-4 rounded text-brand-solid focus:ring-brand" /> 80%
        </label>
        <label class="inline-flex h-9 cursor-pointer items-center gap-2 rounded-full px-3 text-sm ring-1 ring-line">
          <input v-model="alert100" type="checkbox" class="size-4 rounded text-brand-solid focus:ring-brand" /> 100%
        </label>
      </div>
      <p class="mt-1.5 text-[13px] text-ink-muted">You're always told when a budget goes over.</p>
    </fieldset>

    <p v-if="error" role="alert" class="rounded-tile bg-expense-soft/60 p-3 text-sm text-ink">{{ error }}</p>
    <div class="flex gap-2">
      <button type="button" class="h-12 rounded-full px-5 font-medium text-ink-muted hover:bg-ink/[0.05]" @click="emit('cancel')">Cancel</button>
      <button type="submit" class="flex h-12 flex-1 items-center justify-center gap-2 rounded-full bg-brand-solid font-semibold text-white disabled:opacity-70" :disabled="saving">
        <AppIcon v-if="saving" name="refresh-cw" class="size-5 animate-spin" />
        {{ b ? 'Save changes' : 'Create budget' }}
      </button>
    </div>
  </form>
</template>
