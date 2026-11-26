import { defineStore } from 'pinia'
import type { TransactionRowData, TransactionType } from '@/types/finance'

/** Global UI state: the transaction sheet is reachable from every screen. */
export const useUiStore = defineStore('ui', {
  state: () => ({
    quickAddOpen: false,
    quickAddType: 'Expense' as TransactionType,
    /** Preselected account (e.g. when adding from an account's page). */
    quickAddAccount: null as string | null,
    /** Set when the sheet edits an existing transaction. */
    editing: null as TransactionRowData | null,
  }),
  actions: {
    openQuickAdd(type: TransactionType = 'Expense', account: string | null = null) {
      this.editing = null
      this.quickAddType = type
      this.quickAddAccount = account
      this.quickAddOpen = true
    },
    openEdit(txn: TransactionRowData) {
      this.editing = txn
      this.quickAddType = txn.transaction_type
      this.quickAddOpen = true
    },
    closeQuickAdd() {
      this.quickAddOpen = false
    },
  },
})
