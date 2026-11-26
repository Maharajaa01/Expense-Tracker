<script setup lang="ts">
import { computed, ref } from 'vue'
import { dialog, toast } from 'frappe-ui'
import AppIcon from '@/components/ui/AppIcon.vue'
import CategoryIcon from '@/components/ui/CategoryIcon.vue'
import Money from '@/components/ui/Money.vue'
import ReceiptList from './ReceiptList.vue'
import { ApiError } from '@/services/api'
import { transactionsApi } from '@/services/finance'
import { useFinanceStore } from '@/stores/finance'
import { useSyncStore } from '@/stores/sync'
import { useUiStore } from '@/stores/ui'
import type { TransactionRowData } from '@/types/finance'
import { dayLabel, fromISO } from '@/utils/date'
import { formatMoney } from '@/utils/money'

const props = defineProps<{ txn: TransactionRowData }>()
const emit = defineEmits<{ close: [] }>()
const ui = useUiStore()
const finance = useFinanceStore()
const sync = useSyncStore()

const isTransfer = computed(() => props.txn.transaction_type === 'Transfer')
const inflow = computed(() => props.txn.transaction_type === 'Income' || !!props.txn.is_refund)
const fullDate = computed(() =>
  new Intl.DateTimeFormat('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(fromISO(props.txn.transaction_date)),
)
const locked = computed(() => !!props.txn.savings_goal)
const deleting = ref(false)

const facts = computed(() => {
  const t = props.txn
  const list: { label: string; value: string }[] = [
    { label: 'Type', value: t.is_refund ? 'Refund' : t.transaction_type },
    { label: 'Date', value: `${fullDate.value}${['Today', 'Yesterday'].includes(dayLabel(t.transaction_date)) ? ` (${dayLabel(t.transaction_date)})` : ''}` },
  ]
  if (isTransfer.value) {
    list.push({ label: 'From', value: t.account_name }, { label: 'To', value: t.to_account_name ?? '' })
  } else {
    list.push({ label: 'Category', value: t.category_name ?? '' }, { label: t.transaction_type === 'Income' ? 'Received in' : 'Paid from', value: t.account_name })
  }
  if (t.source && t.source !== 'Manual') list.push({ label: 'Added by', value: t.source })
  return list
})

function edit() {
  emit('close')
  ui.openEdit(props.txn)
}

function remove() {
  dialog.danger({
    title: 'Delete this transaction?',
    message: `${props.txn.title}, ${formatMoney(props.txn.amount)}. Account balances will be recalculated. This cannot be undone.`,
    confirmLabel: 'Delete',
    onConfirm: async () => {
      deleting.value = true
      const offline = async () => {
        if (!(await sync.enqueue('delete', { name: props.txn.name }))) throw new Error('You are offline and this browser cannot store changes.')
        toast.success(props.txn.pending ? 'Removed from this device' : 'Deleted on this device. It will sync when you are online.')
        emit('close')
      }
      try {
        if (!sync.online || props.txn.pending) return await offline()
        await transactionsApi.remove(props.txn.name)
        toast.success('Transaction deleted')
        await finance.changed()
        emit('close')
      } catch (e) {
        if (e instanceof ApiError && e.kind === 'network') return await offline()
        throw new Error(e instanceof ApiError ? e.message : 'Could not delete the transaction.')
      } finally {
        deleting.value = false
      }
    },
  })
}
</script>

<template>
  <div class="pb-2">
    <div class="flex flex-col items-center pb-5 pt-2 text-center">
      <CategoryIcon
        :icon="isTransfer ? 'arrow-left-right' : txn.category_icon"
        :color="isTransfer ? '#7c3aed' : txn.category_color"
        size="lg"
      />
      <p class="mt-3 text-[15px] font-medium text-ink">{{ txn.title }}</p>
      <Money
        :value="isTransfer || inflow ? txn.amount : -txn.amount"
        :sign="inflow ? 'always' : 'auto'"
        :tone="isTransfer ? 'inherit' : inflow ? 'income' : 'expense'"
        size="xl"
        class="mt-1 text-ink"
      />
    </div>

    <dl class="divide-y divide-line/60 rounded-tile ring-1 ring-line/60">
      <div v-for="f in facts" :key="f.label" class="flex justify-between gap-4 px-4 py-3 text-sm">
        <dt class="text-ink-muted">{{ f.label }}</dt>
        <dd class="text-right font-medium text-ink">{{ f.value }}</dd>
      </div>
      <div v-if="txn.notes" class="px-4 py-3 text-sm">
        <dt class="mb-1 text-ink-muted">Notes</dt>
        <dd class="whitespace-pre-line text-ink">{{ txn.notes }}</dd>
      </div>
    </dl>

    <ReceiptList :transaction="txn.name" :pending="txn.pending" />

    <p v-if="txn.pending" class="mt-3 flex gap-2 text-sm text-ink-muted">
      <AppIcon name="cloud-upload" class="mt-0.5 size-4 shrink-0 text-warn" />
      Saved on this device and waiting to sync. Balances include it once it syncs.
    </p>
    <p v-if="locked" class="mt-3 flex gap-2 text-sm text-ink-muted">
      <AppIcon name="piggy-bank" class="mt-0.5 size-4 shrink-0" />
      This transfer belongs to a savings goal. Change it from the goal.
    </p>

    <div v-else class="mt-5 grid grid-cols-2 gap-2">
      <button
        type="button"
        class="flex h-11 items-center justify-center gap-2 rounded-full font-medium text-expense ring-1 ring-line hover:bg-expense-soft/40 disabled:opacity-60"
        :disabled="deleting"
        @click="remove"
      >
        <AppIcon name="trash-2" class="size-4" /> Delete
      </button>
      <button
        type="button"
        class="flex h-11 items-center justify-center gap-2 rounded-full bg-brand-solid font-semibold text-white"
        @click="edit"
      >
        <AppIcon name="pencil" class="size-4" /> Edit
      </button>
    </div>
  </div>
</template>
