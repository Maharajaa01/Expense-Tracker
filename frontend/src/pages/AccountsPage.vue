<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { dialog, toast } from 'frappe-ui'
import AppCard from '@/components/ui/AppCard.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import CategoryIcon from '@/components/ui/CategoryIcon.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import Money from '@/components/ui/Money.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import ProgressBar from '@/components/ui/ProgressBar.vue'
import ResponsiveSheet from '@/components/ui/ResponsiveSheet.vue'
import SkeletonRows from '@/components/ui/SkeletonRows.vue'
import AccountForm from '@/features/accounts/AccountForm.vue'
import { ACCOUNT_TYPES } from '@/features/accounts/accountTypes'
import { ApiError } from '@/services/api'
import { accountsApi } from '@/services/finance'
import { useFinanceStore } from '@/stores/finance'
import { useUiStore } from '@/stores/ui'
import type { Account } from '@/types/finance'

const finance = useFinanceStore()
const ui = useUiStore()
onMounted(() => finance.load())

const active = computed(() => finance.accounts.filter((a) => !a.is_archived))
const archived = computed(() => finance.accounts.filter((a) => a.is_archived))
const showArchived = ref(false)
const typeLabel = (t: string) => ACCOUNT_TYPES.find((x) => x.value === t)?.label ?? t

const formOpen = ref(false)
const editing = ref<Account | null>(null)
const selected = ref<Account | null>(null)
const actionsOpen = computed({ get: () => !!selected.value, set: (v) => !v && (selected.value = null) })

function openCreate() {
  editing.value = null
  formOpen.value = true
}
function openEdit(a: Account) {
  selected.value = null
  editing.value = a
  formOpen.value = true
}
function usedCredit(a: Account) {
  return a.credit_limit > 0 ? (Math.max(-a.balance, 0) / a.credit_limit) * 100 : null
}

async function setArchived(a: Account, archived: boolean) {
  selected.value = null
  try {
    await accountsApi.setArchived(a.name, archived)
    toast.success(archived ? 'Account archived' : 'Account restored')
    await finance.changed()
  } catch (e) {
    toast.error(e instanceof ApiError ? e.message : 'Could not update the account.')
  }
}

function remove(a: Account) {
  selected.value = null
  dialog.danger({
    title: `Delete ${a.account_name}?`,
    message: 'This account has no transactions. Deleting it cannot be undone.',
    confirmLabel: 'Delete',
    onConfirm: async () => {
      try {
        await accountsApi.remove(a.name)
        finance.removeAccount(a.name)
        toast.success('Account deleted')
        await finance.changed()
      } catch (e) {
        throw new Error(e instanceof ApiError ? e.message : 'Could not delete the account.')
      }
    },
  })
}
</script>

<template>
  <div>
    <PageHeader title="Accounts">
      <template #actions>
        <button type="button" class="inline-flex h-10 items-center gap-1.5 rounded-full bg-brand-solid px-4 text-sm font-semibold text-white" @click="openCreate">
          <AppIcon name="plus" class="size-4" /> Add account
        </button>
      </template>
    </PageHeader>

    <ErrorState v-if="finance.error && !finance.loaded" :message="finance.error" :retrying="finance.loading" @retry="finance.load(true)" />

    <div v-else-if="!finance.loaded" class="rounded-card bg-card px-3 ring-1 ring-line/60"><SkeletonRows :rows="4" /></div>

    <template v-else>
      <AppCard v-if="finance.totals" variant="brand" padding="lg" class="mb-5">
        <p class="text-sm text-white/80">Net worth</p>
        <Money :value="finance.totals.net_worth" size="hero" class="mt-2 block" />
        <div class="mt-4 flex flex-wrap gap-x-6 gap-y-1 text-sm text-white/85">
          <span>You have <Money :value="finance.totals.assets" size="sm" class="font-semibold text-white" /></span>
          <span v-if="finance.totals.liabilities">You owe <Money :value="finance.totals.liabilities" size="sm" class="font-semibold text-white" /></span>
        </div>
      </AppCard>

      <div v-if="!active.length" class="rounded-card bg-card ring-1 ring-line/60">
        <EmptyState icon="wallet" title="No active accounts" message="Add the bank accounts, cards and wallets you spend from.">
          <button type="button" class="h-10 rounded-full bg-brand-solid px-5 text-sm font-semibold text-white" @click="openCreate">Add account</button>
        </EmptyState>
      </div>

      <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <button
          v-for="a in active"
          :key="a.name"
          type="button"
          class="rounded-card bg-card p-4 text-left ring-1 ring-line/60 transition-shadow hover:shadow-card focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand"
          @click="selected = a"
        >
          <div class="flex items-center gap-3">
            <CategoryIcon :icon="a.icon" :color="a.color" />
            <div class="min-w-0 flex-1">
              <p class="truncate font-semibold text-ink">{{ a.account_name }}</p>
              <p class="text-[13px] text-ink-muted">
                {{ typeLabel(a.account_type) }}<template v-if="!a.include_in_totals">, not in total</template>
              </p>
            </div>
          </div>
          <Money :value="a.balance" tone="auto" size="lg" class="mt-4 block text-ink" />
          <template v-if="a.account_type === 'Credit Card' && a.credit_limit > 0">
            <ProgressBar :percent="usedCredit(a)" :label="`${Math.round(usedCredit(a) ?? 0)}% of limit used`" height="sm" class="mt-3" />
            <p class="mt-1.5 text-xs text-ink-muted">
              <Money :value="a.available_credit ?? 0" size="sm" /> available of <Money :value="a.credit_limit" size="sm" hide-fraction />
            </p>
          </template>
        </button>
      </div>

      <section v-if="archived.length" class="mt-8">
        <button type="button" class="mb-3 inline-flex items-center gap-1 text-sm font-medium text-ink-muted hover:text-ink" :aria-expanded="showArchived" @click="showArchived = !showArchived">
          <AppIcon name="chevron-right" class="size-4 transition-transform" :class="{ 'rotate-90': showArchived }" />
          Archived ({{ archived.length }})
        </button>
        <div v-if="showArchived" class="rounded-card bg-card p-1.5 ring-1 ring-line/60">
          <button v-for="a in archived" :key="a.name" type="button" class="flex w-full items-center gap-3 rounded-tile px-2 py-2.5 text-left opacity-75 hover:bg-ink/[0.03]" @click="selected = a">
            <CategoryIcon :icon="a.icon" :color="a.color" size="sm" />
            <span class="flex-1 text-[15px] text-ink">{{ a.account_name }}</span>
            <Money :value="a.balance" size="sm" tone="muted" />
          </button>
        </div>
      </section>
    </template>

    <!-- Account actions -->
    <ResponsiveSheet v-model:open="actionsOpen" :title="selected?.account_name" size="md">
      <div v-if="selected" class="space-y-1 pb-2">
        <RouterLink :to="{ name: 'transactions', query: { account: selected.name } }" class="flex h-12 items-center gap-3 rounded-tile px-3 text-[15px] text-ink hover:bg-ink/[0.04]" @click="selected = null">
          <AppIcon name="calendar" class="size-5 text-ink-muted" /> View history
        </RouterLink>
        <button v-if="!selected.is_archived" type="button" class="flex h-12 w-full items-center gap-3 rounded-tile px-3 text-[15px] text-ink hover:bg-ink/[0.04]" @click="ui.openQuickAdd('Transfer', selected.name); selected = null">
          <AppIcon name="arrow-left-right" class="size-5 text-ink-muted" /> Transfer money
        </button>
        <button type="button" class="flex h-12 w-full items-center gap-3 rounded-tile px-3 text-[15px] text-ink hover:bg-ink/[0.04]" @click="openEdit(selected)">
          <AppIcon name="pencil" class="size-5 text-ink-muted" /> Edit
        </button>
        <button type="button" class="flex h-12 w-full items-center gap-3 rounded-tile px-3 text-[15px] text-ink hover:bg-ink/[0.04]" @click="setArchived(selected, !selected.is_archived)">
          <AppIcon :name="selected.is_archived ? 'rotate-ccw' : 'archive'" class="size-5 text-ink-muted" />
          {{ selected.is_archived ? 'Restore' : 'Archive' }}
        </button>
        <button v-if="!selected.has_transactions" type="button" class="flex h-12 w-full items-center gap-3 rounded-tile px-3 text-[15px] text-expense hover:bg-expense-soft/40" @click="remove(selected)">
          <AppIcon name="trash-2" class="size-5" /> Delete
        </button>
        <p v-else class="px-3 pt-2 text-[13px] text-ink-muted">Accounts with transactions can be archived but not deleted, so your history stays correct.</p>
      </div>
    </ResponsiveSheet>

    <ResponsiveSheet v-model:open="formOpen" :title="editing ? 'Edit account' : 'Add account'" size="xl">
      <AccountForm v-if="formOpen" :account="editing" @saved="formOpen = false" @cancel="formOpen = false" />
    </ResponsiveSheet>
  </div>
</template>
