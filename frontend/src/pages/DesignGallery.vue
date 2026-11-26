<script setup lang="ts">
/**
 * Design review page. Only included in builds made with VITE_DESIGN_GALLERY=1,
 * never in the production bundle. Values below are illustrative.
 */
import { ref } from 'vue'
import AmountInput from '@/components/ui/AmountInput.vue'
import AppCard from '@/components/ui/AppCard.vue'
import CategoryIcon from '@/components/ui/CategoryIcon.vue'
import ColorPicker from '@/components/ui/ColorPicker.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import IconPicker from '@/components/ui/IconPicker.vue'
import Money from '@/components/ui/Money.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import ProgressBar from '@/components/ui/ProgressBar.vue'
import ProgressRing from '@/components/ui/ProgressRing.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import SkeletonRows from '@/components/ui/SkeletonRows.vue'
import StatTile from '@/components/ui/StatTile.vue'
import TransactionRow from '@/components/ui/TransactionRow.vue'
import type { TransactionRowData, TransactionType } from '@/types/finance'

const type = ref<TransactionType>('Expense')
const amount = ref('1250')
const color = ref('#f97316')
const icon = ref('utensils')

const base = { account: 'a', account_name: 'HDFC Savings', is_refund: 0 as const, transaction_date: '2026-11-23' }
const rows: TransactionRowData[] = [
  { ...base, name: '1', transaction_type: 'Expense', amount: 420, title: 'Lunch at Saravana Bhavan', category_name: 'Food & Dining', category_icon: 'utensils', category_color: '#f97316', has_attachments: 1 },
  { ...base, name: '2', transaction_type: 'Income', amount: 85000, title: 'November salary', category_name: 'Salary', category_icon: 'briefcase', category_color: '#16a34a' },
  { ...base, name: '3', transaction_type: 'Transfer', amount: 12000, title: 'Card bill', to_account_name: 'ICICI Card' },
  { ...base, name: '4', transaction_type: 'Expense', amount: 1899, is_refund: 1, title: 'Returned shoes', category_name: 'Shopping', category_icon: 'shopping-bag', category_color: '#ec4899' },
  { ...base, name: '5', transaction_type: 'Expense', amount: 60, title: 'Auto', category_name: 'Transportation', category_icon: 'bus', category_color: '#3b82f6', pending: true },
]
</script>

<template>
  <div class="space-y-6">
    <PageHeader title="Design gallery" subtitle="Component review build. Values are illustrative." />

    <AppCard variant="brand" padding="lg">
      <p class="text-sm text-white/80">Total balance</p>
      <Money :value="248315.5" size="hero" class="mt-2 block" />
      <p class="mt-3 text-sm text-white/80">Across 4 accounts</p>
    </AppCard>

    <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <StatTile label="Income" :value="85000" icon="arrow-down-left" tone="income" hint="This month" />
      <StatTile label="Spent" :value="41230.75" icon="arrow-up-right" tone="expense" hint="48% of income" />
      <StatTile label="Saved" :value="43769.25" icon="piggy-bank" tone="savings" hint="51.5% savings rate" />
      <StatTile label="Loading" :value="0" icon="wallet" tone="accent" loading />
    </div>

    <AppCard>
      <h2 class="mb-2 font-semibold text-ink">Transactions</h2>
      <TransactionRow v-for="r in rows" :key="r.name" :txn="r" />
    </AppCard>

    <AppCard>
      <h2 class="mb-4 font-semibold text-ink">Quick add parts</h2>
      <SegmentedControl
        v-model="type"
        label="Transaction type"
        :options="[
          { value: 'Expense', label: 'Expense', tone: 'expense' },
          { value: 'Income', label: 'Income', tone: 'income' },
          { value: 'Transfer', label: 'Transfer', tone: 'accent' },
        ]"
      />
      <div class="py-6">
        <AmountInput v-model="amount" :tone="type === 'Income' ? 'income' : type === 'Transfer' ? 'brand' : 'expense'" />
      </div>
      <div class="grid gap-6 sm:grid-cols-2">
        <IconPicker v-model="icon" :color="color" />
        <ColorPicker v-model="color" />
      </div>
      <div class="mt-4 flex items-center gap-3">
        <CategoryIcon :icon="icon" :color="color" size="sm" />
        <CategoryIcon :icon="icon" :color="color" />
        <CategoryIcon :icon="icon" :color="color" size="lg" />
      </div>
    </AppCard>

    <AppCard>
      <h2 class="mb-4 font-semibold text-ink">Budgets</h2>
      <div class="flex flex-wrap items-center gap-6">
        <ProgressRing :percent="34" label="Food budget" />
        <ProgressRing :percent="86" label="Shopping budget" />
        <ProgressRing :percent="112" label="Fuel budget" />
        <ProgressRing :percent="64" tone="savings" label="Emergency fund" :size="96" :stroke="10" />
      </div>
      <div class="mt-6 space-y-4">
        <ProgressBar :percent="34" label="34%" />
        <ProgressBar :percent="86" label="86%" />
        <ProgressBar :percent="112" label="112%" />
      </div>
    </AppCard>

    <div class="grid gap-4 sm:grid-cols-2">
      <AppCard><EmptyState icon="inbox" title="No transactions yet" message="Add your first expense to see it here." /></AppCard>
      <AppCard>
        <ErrorState message="Couldn't load your accounts. Check your connection." />
        <div class="mt-4"><SkeletonRows :rows="3" /></div>
      </AppCard>
    </div>
  </div>
</template>
