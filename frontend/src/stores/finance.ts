import { defineStore } from 'pinia'
import { readThrough } from '@/offline/cache'
import { accountsApi, categoriesApi, type AccountTotals } from '@/services/finance'
import { boot } from '@/services/boot'
import type { Account, Category } from '@/types/finance'

/**
 * Reference data used across screens (accounts, categories) plus a
 * `dataVersion` counter. Anything that changes money bumps the version, and
 * screens showing figures watch it to refetch from the server.
 */
export const useFinanceStore = defineStore('finance', {
  state: () => ({
    accounts: [] as Account[],
    /** Server-computed; never summed in the browser. */
    totals: null as AccountTotals | null,
    categories: [] as Category[],
    loaded: false,
    loading: false,
    error: null as string | null,
    dataVersion: 0,
    /** When reference data came from the device instead of the server. */
    savedAt: null as number | null,
    lastUsedAccount: boot.data?.profile?.last_used_account ?? null,
    defaultAccount: boot.data?.profile?.default_account ?? null,
  }),
  getters: {
    activeAccounts: (s) => s.accounts.filter((a) => !a.is_archived),
    accountMap: (s) => new Map(s.accounts.map((a) => [a.name, a])),
    categoryMap: (s) => new Map(s.categories.map((c) => [c.name, c])),
  },
  actions: {
    async load(force = false) {
      if (this.loading || (this.loaded && !force)) return
      this.loading = true
      this.error = null
      try {
        const [acc, categories] = await Promise.all([
          readThrough('accounts', () => accountsApi.list(true)),
          readThrough('categories', () => categoriesApi.list(true)),
        ])
        this.accounts = acc.data.accounts
        this.totals = acc.data.totals
        this.categories = categories.data
        this.savedAt = acc.savedAt ?? categories.savedAt
        this.loaded = true
      } catch (e: any) {
        this.error = e?.message ?? 'Could not load your accounts and categories.'
      } finally {
        this.loading = false
      }
    },
    /** Call after any write that changes balances or totals. */
    async changed() {
      this.dataVersion++
      // Balances live on accounts, so refresh them from the server.
      await this.reloadAccounts()
    },
    async reloadAccounts() {
      try {
        const acc = await readThrough('accounts', () => accountsApi.list(true))
        this.accounts = acc.data.accounts
        this.totals = acc.data.totals
        this.savedAt = acc.savedAt
      } catch {
        /* screens show their own errors; stale balances refresh on next load */
      }
    },
    upsertAccount(a: Account) {
      const i = this.accounts.findIndex((x) => x.name === a.name)
      i === -1 ? this.accounts.push(a) : this.accounts.splice(i, 1, a)
    },
    removeAccount(name: string) {
      this.accounts = this.accounts.filter((a) => a.name !== name)
    },
    upsertCategory(c: Category) {
      const i = this.categories.findIndex((x) => x.name === c.name)
      i === -1 ? this.categories.push(c) : this.categories.splice(i, 1, c)
    },
    async reloadCategories() {
      this.categories = await categoriesApi.list(true)
    },
    /** Expense or income categories, parents first with their children after. */
    categoryTree(type: 'Expense' | 'Income', includeArchived = false) {
      const list = this.categories.filter((c) => c.category_type === type && (includeArchived || !c.is_archived))
      const parents = list.filter((c) => !c.parent_category).sort((a, b) => a.sort_order - b.sort_order)
      return parents.map((p) => ({
        ...p,
        children: list.filter((c) => c.parent_category === p.name).sort((a, b) => a.category_name.localeCompare(b.category_name)),
      }))
    },
  },
})
