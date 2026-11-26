/**
 * INR formatting with Indian digit grouping (1,23,456.78).
 * Display-only: the frontend never does balance arithmetic.
 */
const full = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})
const compact = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  notation: 'compact',
  maximumFractionDigits: 1,
})

export interface MoneyParts {
  negative: boolean
  symbol: string
  integer: string
  fraction: string
}

export function moneyParts(value: number): MoneyParts {
  const v = Number.isFinite(value) ? value : 0
  const parts = full.formatToParts(Math.abs(v))
  return {
    negative: v < 0 && Math.abs(v) >= 0.005,
    symbol: parts.find((p) => p.type === 'currency')?.value ?? '₹',
    integer: parts.filter((p) => p.type === 'integer' || p.type === 'group').map((p) => p.value).join(''),
    fraction: parts.find((p) => p.type === 'fraction')?.value ?? '00',
  }
}

/** Plain string, e.g. for aria-labels, chart tooltips and toasts. */
export function formatMoney(value: number, opts: { compact?: boolean; signed?: boolean } = {}): string {
  const v = Number.isFinite(value) ? value : 0
  const body = (opts.compact ? compact : full).format(Math.abs(v))
  if (v < 0) return `−${body}`
  if (opts.signed && v > 0) return `+${body}`
  return body
}

export const MAX_AMOUNT = 999_999_999_999.99

/**
 * Normalise what a person types into an amount field: digits and a single
 * decimal point, at most 2 decimals, no leading zeros. Returns the cleaned
 * string so the caret position stays predictable.
 */
export function sanitizeAmountInput(raw: string): string {
  let s = raw.replace(/,/g, '').replace(/[^\d.]/g, '')
  const dot = s.indexOf('.')
  if (dot !== -1) s = s.slice(0, dot + 1) + s.slice(dot + 1).replace(/\./g, '')
  let [int, frac] = s.split('.') as [string, string | undefined]
  int = int.replace(/^0+(?=\d)/, '').slice(0, 12)
  if (frac !== undefined) return `${int || '0'}.${frac.slice(0, 2)}`
  return int
}

/** Parse a sanitised amount; `null` when empty or not a positive number. */
export function parseAmount(s: string): number | null {
  if (!s || s === '.') return null
  const n = Number(s)
  if (!Number.isFinite(n) || n <= 0 || n > MAX_AMOUNT) return null
  return Math.round(n * 100) / 100
}
