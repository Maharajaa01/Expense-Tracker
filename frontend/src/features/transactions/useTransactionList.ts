import { computed, ref, watch, type Ref } from 'vue'
import { readThrough } from '@/offline/cache'
import { usePendingRows } from '@/offline/pendingRows'
import { ApiError } from '@/services/api'
import { transactionsApi } from '@/services/finance'
import { useFinanceStore } from '@/stores/finance'
import type { DayTotals, SortKey, TransactionFilters, TransactionRowData } from '@/types/finance'

export interface DayGroup {
  date: string
  rows: TransactionRowData[]
  totals: DayTotals
}

/**
 * Paginated, server-filtered transaction list. Only one page at a time is
 * fetched (never the whole history). Responses from superseded requests are
 * dropped so fast filter changes can't show stale rows.
 */
export function useTransactionList(filters: Ref<TransactionFilters>, sort: Ref<SortKey>, pageSize = 50) {
  const finance = useFinanceStore()
  const pendingRows = usePendingRows()
  const serverRows = ref<TransactionRowData[]>([])
  const savedAt = ref<number | null>(null)
  const dayTotals = ref<Record<string, DayTotals>>({})
  const summary = ref<{ income: number; expense: number } | null>(null)
  const total = ref<number | null>(null)
  const page = ref(0)
  const hasMore = ref(false)
  const loading = ref(false)
  const loadingMore = ref(false)
  const error = ref<string | null>(null)
  let seq = 0

  async function fetchPage(next: number) {
    const id = ++seq
    next === 1 ? (loading.value = true) : (loadingMore.value = true)
    error.value = null
    try {
      const fetcher = () => transactionsApi.list(filters.value, next, pageSize, sort.value)
      // Only the unfiltered first page is kept for offline viewing.
      const cached = next === 1 && isDefaultView() ? await readThrough('transactions:recent', fetcher) : { data: await fetcher(), savedAt: null }
      const res = cached.data
      if (id !== seq) return
      savedAt.value = cached.savedAt
      serverRows.value = next === 1 ? res.rows : [...serverRows.value, ...res.rows]
      dayTotals.value = next === 1 ? res.day_totals : { ...dayTotals.value, ...res.day_totals }
      if (res.summary) summary.value = res.summary
      if (res.meta.total !== undefined) total.value = res.meta.total
      page.value = next
      hasMore.value = res.meta.has_more
    } catch (e) {
      if (id !== seq) return
      error.value = e instanceof ApiError ? e.message : 'Could not load transactions.'
    } finally {
      if (id === seq) {
        loading.value = false
        loadingMore.value = false
      }
    }
  }

  function isDefaultView() {
    const f = filters.value
    return sort.value === 'date_desc' && !f.q && !f.type && !f.account && !f.category && !f.from_date && !f.to_date
  }

  /** Server rows with queued offline edits/deletes applied, plus queued new entries on top. */
  const rows = computed<TransactionRowData[]>(() => [
    ...(isDefaultView() ? pendingRows.created.value : []),
    ...pendingRows.overlay(serverRows.value),
  ])

  const reload = () => fetchPage(1)
  const loadMore = () => {
    if (hasMore.value && !loadingMore.value && !loading.value) fetchPage(page.value + 1)
  }

  watch([filters, sort], reload, { deep: true, immediate: true })
  watch(() => finance.dataVersion, reload)

  /** Date groups only make sense when sorted by date. */
  const groups = computed<DayGroup[]>(() => {
    if (!sort.value.startsWith('date')) return []
    const out: DayGroup[] = []
    for (const r of rows.value) {
      const last = out[out.length - 1]
      if (last && last.date === r.transaction_date) last.rows.push(r)
      else out.push({ date: r.transaction_date, rows: [r], totals: dayTotals.value[r.transaction_date] ?? { income: 0, expense: 0 } })
    }
    return out
  })

  return { rows, groups, summary, total, hasMore, loading, loadingMore, error, reload, loadMore, savedAt }
}
