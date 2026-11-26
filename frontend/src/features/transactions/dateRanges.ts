import { toISO } from '@/utils/date'

export type RangeKey = 'all' | 'this_month' | 'last_month' | 'last_3_months' | 'this_year' | 'custom'

export const RANGE_OPTIONS: { value: RangeKey; label: string }[] = [
  { value: 'all', label: 'All time' },
  { value: 'this_month', label: 'This month' },
  { value: 'last_month', label: 'Last month' },
  { value: 'last_3_months', label: 'Last 3 months' },
  { value: 'this_year', label: 'This year' },
  { value: 'custom', label: 'Custom range' },
]

/** Concrete from/to dates for a preset (local calendar). */
export function rangeDates(key: RangeKey, now = new Date()): { from_date?: string; to_date?: string } {
  const y = now.getFullYear()
  const m = now.getMonth()
  switch (key) {
    case 'this_month':
      return { from_date: toISO(new Date(y, m, 1)), to_date: toISO(new Date(y, m + 1, 0)) }
    case 'last_month':
      return { from_date: toISO(new Date(y, m - 1, 1)), to_date: toISO(new Date(y, m, 0)) }
    case 'last_3_months':
      return { from_date: toISO(new Date(y, m - 2, 1)), to_date: toISO(new Date(y, m + 1, 0)) }
    case 'this_year':
      return { from_date: toISO(new Date(y, 0, 1)), to_date: toISO(new Date(y, 11, 31)) }
    default:
      return {}
  }
}
