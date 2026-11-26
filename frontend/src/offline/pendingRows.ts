import { computed } from 'vue'
import { useFinanceStore } from '@/stores/finance'
import { useSyncStore } from '@/stores/sync'
import type { TransactionRowData } from '@/types/finance'

/**
 * Display helpers for changes waiting to sync. Rows are for showing only;
 * balances and totals stay as the server last reported them.
 */
export function usePendingRows() {
  const sync = useSyncStore()
  const finance = useFinanceStore()

  const created = computed<TransactionRowData[]>(() =>
    sync.pendingCreates.map((i) => {
      const d = i.data ?? {}
      const cat = d.category ? finance.categoryMap.get(d.category) : undefined
      return {
        name: i.id,
        client_txn_id: i.id,
        transaction_type: d.transaction_type ?? 'Expense',
        transaction_date: d.transaction_date ?? '',
        amount: Number(d.amount ?? 0),
        is_refund: (d.is_refund ?? 0) as 0 | 1,
        title: d.title || cat?.category_name || (d.transaction_type === 'Transfer' ? 'Transfer' : d.transaction_type ?? ''),
        notes: d.notes ?? null,
        account: d.account ?? '',
        account_name: finance.accountMap.get(d.account ?? '')?.account_name ?? '',
        to_account: d.to_account ?? null,
        to_account_name: d.to_account ? finance.accountMap.get(d.to_account)?.account_name ?? '' : null,
        category: d.category ?? null,
        category_name: cat?.category_name ?? null,
        category_icon: cat?.icon ?? null,
        category_color: cat?.color ?? null,
        pending: true,
      }
    }).sort((a, b) => b.transaction_date.localeCompare(a.transaction_date)),
  )

  /** Apply queued edits/deletes to server rows and mark them pending. */
  function overlay(rows: TransactionRowData[]): TransactionRowData[] {
    return rows
      .filter((r) => !sync.pendingDeletes.has(r.name))
      .map((r) => {
        const u = sync.pendingUpdates.get(r.name)
        if (!u) return r
        const d = u.data ?? {}
        const cat = d.category ? finance.categoryMap.get(d.category) : undefined
        return {
          ...r, ...d, pending: true,
          amount: d.amount !== undefined ? Number(d.amount) : r.amount,
          title: d.title || r.title,
          ...(cat ? { category_name: cat.category_name, category_icon: cat.icon, category_color: cat.color } : {}),
        } as TransactionRowData
      })
  }

  return { created, overlay }
}
