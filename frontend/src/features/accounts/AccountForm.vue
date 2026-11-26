<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { toast } from 'frappe-ui'
import AmountInput from '@/components/ui/AmountInput.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import CategoryIcon from '@/components/ui/CategoryIcon.vue'
import ColorPicker from '@/components/ui/ColorPicker.vue'
import IconPicker from '@/components/ui/IconPicker.vue'
import { ApiError } from '@/services/api'
import { accountsApi } from '@/services/finance'
import { useFinanceStore } from '@/stores/finance'
import type { Account, AccountType } from '@/types/finance'
import { parseAmount } from '@/utils/money'
import { ACCOUNT_TYPES } from './accountTypes'

const props = defineProps<{ account?: Account | null }>()
const emit = defineEmits<{ saved: [a: Account]; cancel: [] }>()
const finance = useFinanceStore()
const a = props.account

const name = ref(a?.account_name ?? '')
const last4 = ref(a?.account_last4 ?? '')
const type = ref<AccountType>(a?.account_type ?? 'Savings Account')
const isCard = computed(() => type.value === 'Credit Card')
// Credit cards are entered as "dues owed" (stored as a negative opening balance).
const opening = ref(a ? String(Math.abs(a.opening_balance) || '') : '')
const openingNegative = ref(a ? a.opening_balance < 0 : false)
const openingDate = ref(a?.opening_date ?? '')
const creditLimit = ref(a?.credit_limit ? String(a.credit_limit) : '')
const icon = ref(a?.icon ?? 'piggy-bank')
const color = ref(a?.color ?? '#0d9488')
const includeInTotals = ref(a ? !!a.include_in_totals : true)
const notes = ref(a?.notes ?? '')
const saving = ref(false)
const error = ref<string | null>(null)
const nameError = ref<string | null>(null)

// New accounts: pick a sensible icon/colour when the type changes.
watch(type, (t) => {
  if (a) return
  const def = ACCOUNT_TYPES.find((x) => x.value === t)!
  icon.value = def.icon
  color.value = def.color
})

async function save() {
  if (saving.value) return
  nameError.value = name.value.trim() ? null : 'Give the account a name.'
  if (nameError.value) return
  const openingValue = opening.value ? parseAmount(opening.value) ?? 0 : 0
  saving.value = true
  error.value = null
  try {
    const data: Partial<Account> = {
      account_name: name.value.trim(),
      account_type: type.value,
      // Card dues are always money owed; other accounts are negative only if overdrawn.
      opening_balance: isCard.value || openingNegative.value ? -openingValue : openingValue,
      opening_date: openingDate.value || null,
      credit_limit: isCard.value ? parseAmount(creditLimit.value) ?? 0 : 0,
      icon: icon.value,
      color: color.value,
      include_in_totals: includeInTotals.value ? 1 : 0,
      notes: notes.value.trim() || null,
      account_last4: last4.value.trim() || null,
    }
    const saved = a ? await accountsApi.update(a.name, data) : await accountsApi.create(data)
    toast.success(a ? 'Account updated' : 'Account added')
    await finance.changed()
    emit('saved', saved)
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Could not save the account.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <form class="space-y-5 pt-1" novalidate @submit.prevent="save">
    <div class="flex items-center gap-3">
      <CategoryIcon :icon="icon" :color="color" size="lg" />
      <label class="flex-1">
        <span class="mb-1.5 block text-sm font-medium text-ink">Account name</span>
        <input
          v-model="name"
          maxlength="100"
          placeholder="e.g. HDFC Savings"
          :aria-invalid="!!nameError"
          class="h-11 w-full rounded-tile border-0 bg-card px-3 text-[15px] text-ink ring-1 ring-line focus:ring-2 focus:ring-brand"
        />
      </label>
    </div>
    <p v-if="nameError" role="alert" class="-mt-3 text-sm text-expense">{{ nameError }}</p>

    <fieldset>
      <legend class="mb-2 text-sm font-medium text-ink">Type</legend>
      <div class="grid grid-cols-3 gap-2">
        <button
          v-for="t in ACCOUNT_TYPES"
          :key="t.value"
          type="button"
          :aria-pressed="type === t.value"
          class="flex flex-col items-center gap-1 rounded-tile px-2 py-2.5 text-[13px] font-medium ring-1 transition-colors"
          :class="type === t.value ? 'bg-brand-soft text-brand-ink ring-2 ring-brand' : 'text-ink-muted ring-line hover:text-ink'"
          @click="type = t.value"
        >
          <AppIcon :name="t.icon" class="size-5" />
          {{ t.label }}
        </button>
      </div>
    </fieldset>

    <section class="rounded-tile bg-ink/[0.03] p-4 ring-1 ring-line/60">
      <h3 class="text-center text-sm font-medium text-ink">
        {{ isCard ? 'Amount you currently owe' : 'Balance when you start tracking' }}
      </h3>
      <AmountInput v-model="opening" :tone="isCard || openingNegative ? 'expense' : 'brand'" :label="isCard ? 'Current dues' : 'Opening balance'" class="py-2" />
      <label v-if="!isCard" class="mt-1 flex items-center justify-center gap-2 text-sm text-ink-muted">
        <input v-model="openingNegative" type="checkbox" class="size-4 rounded text-brand-solid focus:ring-brand" />
        This balance is negative (overdrawn)
      </label>
      <label class="mt-3 block text-sm">
        <span class="mb-1.5 block font-medium text-ink">As of <span class="font-normal text-ink-faint">(optional)</span></span>
        <input v-model="openingDate" type="date" class="h-10 w-full rounded-[10px] border-0 bg-card px-3 text-ink ring-1 ring-line focus:ring-2 focus:ring-brand" />
      </label>
    </section>

    <label v-if="type !== 'Cash'" class="block">
      <span class="mb-1.5 block text-sm font-medium text-ink">Last 4 digits of the account or card number <span class="font-normal text-ink-faint">(optional)</span></span>
      <input
        v-model="last4"
        inputmode="numeric"
        maxlength="4"
        pattern="[0-9]{4}"
        placeholder="e.g. 1234"
        class="h-11 w-32 rounded-tile border-0 bg-card px-3 text-[15px] tabular tracking-widest text-ink ring-1 ring-line focus:ring-2 focus:ring-brand"
        @input="last4 = last4.replace(/\D/g, '').slice(0, 4)"
      />
      <span class="mt-1 block text-[13px] text-ink-muted">Matches bank alert emails ("A/c XX1234") to this account.</span>
    </label>

    <label v-if="isCard" class="block">
      <span class="mb-1.5 block text-sm font-medium text-ink">Credit limit</span>
      <input
        v-model="creditLimit"
        inputmode="decimal"
        placeholder="e.g. 100000"
        class="h-11 w-full rounded-tile border-0 bg-card px-3 text-[15px] tabular text-ink ring-1 ring-line focus:ring-2 focus:ring-brand"
      />
    </label>

    <div class="grid gap-5 sm:grid-cols-2">
      <IconPicker v-model="icon" set="account" :color="color" />
      <ColorPicker v-model="color" />
    </div>

    <label class="flex items-start gap-3 text-sm text-ink">
      <input v-model="includeInTotals" type="checkbox" class="mt-0.5 size-4 rounded text-brand-solid focus:ring-brand" />
      <span>
        Include in total balance
        <span class="block text-ink-muted">Turn off for accounts you track but don't count, like a joint account.</span>
      </span>
    </label>

    <label class="block">
      <span class="mb-1.5 block text-sm font-medium text-ink">Notes <span class="font-normal text-ink-faint">(optional)</span></span>
      <textarea v-model="notes" rows="2" class="w-full rounded-tile border-0 bg-card px-3 py-2 text-[15px] text-ink ring-1 ring-line focus:ring-2 focus:ring-brand" />
    </label>

    <p v-if="error" role="alert" class="rounded-tile bg-expense-soft/60 p-3 text-sm text-ink">{{ error }}</p>

    <div class="flex gap-2">
      <button type="button" class="h-12 rounded-full px-5 font-medium text-ink-muted hover:bg-ink/[0.05]" @click="emit('cancel')">Cancel</button>
      <button
        type="submit"
        class="flex h-12 flex-1 items-center justify-center gap-2 rounded-full bg-brand-solid font-semibold text-white disabled:opacity-70"
        :disabled="saving"
      >
        <AppIcon v-if="saving" name="refresh-cw" class="size-5 animate-spin" />
        {{ a ? 'Save changes' : 'Add account' }}
      </button>
    </div>
  </form>
</template>
