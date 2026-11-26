<script setup lang="ts">
import { computed } from 'vue'
import type { TransactionRowData } from '@/types/finance'
import { dayLabel } from '@/utils/date'
import AppIcon from './AppIcon.vue'
import CategoryIcon from './CategoryIcon.vue'
import Money from './Money.vue'

const props = withDefaults(defineProps<{ txn: TransactionRowData; showDate?: boolean }>(), { showDate: false })
defineEmits<{ select: [txn: TransactionRowData] }>()

const isTransfer = computed(() => props.txn.transaction_type === 'Transfer')
/** Money in (income, refund): green with "+". Spending: coral with "−". Transfers: neutral. */
const inflow = computed(
  () => props.txn.transaction_type === 'Income' || (props.txn.transaction_type === 'Expense' && !!props.txn.is_refund),
)
const signed = computed(() => (isTransfer.value ? props.txn.amount : inflow.value ? props.txn.amount : -props.txn.amount))
const subtitle = computed(() => {
  const t = props.txn
  const where = isTransfer.value ? `${t.account_name} to ${t.to_account_name}` : t.account_name
  const what = isTransfer.value ? 'Transfer' : t.is_refund ? `${t.category_name} refund` : t.category_name
  const parts = [what, where]
  if (props.showDate) parts.push(dayLabel(t.transaction_date))
  return parts.filter(Boolean).join(', ')
})
</script>

<template>
  <button
    type="button"
    class="group flex w-full items-center gap-3 rounded-tile px-2 py-2.5 text-left transition-colors hover:bg-ink/[0.03] focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand"
    @click="$emit('select', txn)"
  >
    <CategoryIcon
      :icon="isTransfer ? 'arrow-left-right' : txn.category_icon"
      :color="isTransfer ? '#7c3aed' : txn.category_color"
    />
    <span class="min-w-0 flex-1">
      <span class="flex items-center gap-1.5">
        <span class="truncate text-[15px] font-medium text-ink">{{ txn.title }}</span>
        <AppIcon v-if="txn.has_attachments" name="paperclip" class="size-3.5 text-ink-faint" label="Has receipt" />
        <AppIcon v-if="txn.pending" name="cloud-upload" class="size-3.5 text-warn" label="Waiting to sync" />
        <span v-if="txn.needs_review" class="shrink-0 rounded-full bg-warn-soft px-1.5 py-px text-[10.5px] font-semibold text-warn">To categorise</span>
      </span>
      <span class="block truncate text-[13px] text-ink-muted">{{ subtitle }}</span>
    </span>
    <Money
      :value="signed"
      :sign="inflow ? 'always' : 'auto'"
      :tone="isTransfer ? 'muted' : inflow ? 'income' : 'expense'"
      size="md"
    />
  </button>
</template>
