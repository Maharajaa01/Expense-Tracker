<script setup lang="ts">
import { computed, ref } from 'vue'
import { toast } from 'frappe-ui'
import AmountInput from '@/components/ui/AmountInput.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import SelectField from '@/components/ui/SelectField.vue'
import { ApiError } from '@/services/api'
import { goalsApi } from '@/services/finance'
import { useFinanceStore } from '@/stores/finance'
import type { Goal } from '@/types/finance'
import { todayISO } from '@/utils/date'
import { formatMoney, parseAmount } from '@/utils/money'

const props = defineProps<{ goal: Goal; kind?: 'Contribution' | 'Withdrawal' }>()
const emit = defineEmits<{ saved: [g: Goal]; cancel: [] }>()
const finance = useFinanceStore()
const kind = ref<'Contribution' | 'Withdrawal'>(props.kind ?? 'Contribution')
const amount = ref('')
const date = ref(todayISO())
const source = ref(finance.activeAccounts.find((a) => a.name !== props.goal.linked_account)?.name ?? '')
const note = ref('')
const saving = ref(false)
const error = ref<string | null>(null)
const otherAccounts = computed(() => finance.activeAccounts.filter((a) => a.name !== props.goal.linked_account).map((a) => ({ value: a.name, label: a.account_name })))

async function save() {
  if (saving.value) return
  const value = parseAmount(amount.value)
  if (value === null) {
    error.value = 'Enter an amount.'
    return
  }
  if (props.goal.linked_account && !source.value) {
    error.value = kind.value === 'Contribution' ? 'Choose where the money comes from.' : 'Choose where the money goes.'
    return
  }
  saving.value = true
  error.value = null
  try {
    const saved = await goalsApi.contribute(props.goal.name, {
      amount: value, kind: kind.value, date: date.value,
      source_account: props.goal.linked_account ? source.value : null, note: note.value.trim() || null,
    })
    toast.success(kind.value === 'Contribution' ? `${formatMoney(value)} added to ${props.goal.goal_name}` : `${formatMoney(value)} withdrawn`)
    props.goal.linked_account ? await finance.changed() : finance.dataVersion++
    emit('saved', saved)
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Could not save.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <form class="space-y-5 pt-1" novalidate @submit.prevent="save">
    <SegmentedControl v-model="kind" label="Type" :options="[{ value: 'Contribution', label: 'Add money', tone: 'brand' }, { value: 'Withdrawal', label: 'Withdraw', tone: 'expense' }]" />
    <AmountInput v-model="amount" :tone="kind === 'Contribution' ? 'brand' : 'expense'" autofocus class="py-2" />
    <div v-if="goal.linked_account">
      <SelectField v-model="source" :label="kind === 'Contribution' ? 'From account' : 'To account'" :options="otherAccounts" placeholder="Choose an account" />
      <p class="mt-1 text-[13px] text-ink-muted">
        {{ kind === 'Contribution' ? `Moves the money into ${goal.linked_account_name} as a transfer.` : `Moves the money out of ${goal.linked_account_name} as a transfer.` }}
        Transfers aren't counted as spending or income.
      </p>
    </div>
    <p v-else class="text-[13px] text-ink-muted">This goal isn't linked to an account, so this only updates the goal's progress. No balances change.</p>
    <label class="block text-sm">
      <span class="mb-1.5 block font-medium text-ink">Date</span>
      <input v-model="date" type="date" class="h-10 w-full rounded-[10px] border-0 bg-card px-3 text-ink ring-1 ring-line focus:ring-2 focus:ring-brand" />
    </label>
    <label class="block text-sm">
      <span class="mb-1.5 block font-medium text-ink">Note <span class="font-normal text-ink-faint">(optional)</span></span>
      <input v-model="note" maxlength="140" class="h-10 w-full rounded-[10px] border-0 bg-card px-3 text-ink ring-1 ring-line focus:ring-2 focus:ring-brand" />
    </label>
    <p v-if="error" role="alert" class="rounded-tile bg-expense-soft/60 p-3 text-sm text-ink">{{ error }}</p>
    <div class="flex gap-2">
      <button type="button" class="h-12 rounded-full px-5 font-medium text-ink-muted hover:bg-ink/[0.05]" @click="emit('cancel')">Cancel</button>
      <button type="submit" class="flex h-12 flex-1 items-center justify-center gap-2 rounded-full font-semibold text-white disabled:opacity-70" :class="kind === 'Contribution' ? 'bg-brand-solid' : 'bg-expense-solid'" :disabled="saving">
        <AppIcon v-if="saving" name="refresh-cw" class="size-5 animate-spin" /> {{ kind === 'Contribution' ? 'Add money' : 'Withdraw' }}
      </button>
    </div>
  </form>
</template>
