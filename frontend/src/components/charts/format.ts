import { formatMoney } from '@/utils/money'
import { fromISO } from '@/utils/date'

const month = new Intl.DateTimeFormat('en-IN', { month: 'short' })
const monthYear = new Intl.DateTimeFormat('en-IN', { month: 'long', year: 'numeric' })
const dayMonth = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short' })
const fullDay = new Intl.DateTimeFormat('en-IN', { weekday: 'short', day: 'numeric', month: 'short' })

export type Grain = 'day' | 'week' | 'month'

/** Axis label for a bucket start date. */
export function axisLabel(iso: string, grain: Grain): string {
  const d = fromISO(iso)
  if (grain === 'month') return month.format(d)
  if (grain === 'week') return dayMonth.format(d)
  return String(d.getDate())
}

/** Tooltip / table label for a bucket. */
export function bucketLabel(iso: string, grain: Grain): string {
  const d = fromISO(iso)
  if (grain === 'month') return monthYear.format(d)
  if (grain === 'week') return `Week of ${dayMonth.format(d)}`
  return fullDay.format(d)
}

export const axisMoney = (v: number) => (v === 0 ? '0' : formatMoney(v, { compact: true }))

/** Escape text for ECharts HTML tooltips. */
export function esc(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!)
}

export function swatchRow(color: string, label: string, value: string): string {
  return `<div style="display:flex;align-items:center;gap:8px;line-height:1.7">
    <span style="width:10px;height:10px;border-radius:3px;background:${color}"></span>
    <span style="flex:1">${esc(label)}</span><b style="font-variant-numeric:tabular-nums;margin-left:12px">${esc(value)}</b></div>`
}
