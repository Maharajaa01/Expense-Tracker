/** Date helpers. Dates travel as ISO `YYYY-MM-DD` strings (no timezone). */

export function todayISO(): string {
  const d = new Date()
  return toISO(d)
}

export function toISO(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export function fromISO(s: string): Date {
  const [y, m, d] = s.split('-').map(Number)
  return new Date(y, (m || 1) - 1, d || 1)
}

const dayFmt = new Intl.DateTimeFormat('en-IN', { weekday: 'short', day: 'numeric', month: 'short' })
const dayYearFmt = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
const longFmt = new Intl.DateTimeFormat('en-IN', { weekday: 'long', day: 'numeric', month: 'long' })

/** "Today", "Yesterday", "Mon, 16 Nov" or "16 Nov 2025" for other years. */
export function dayLabel(iso: string, today = todayISO()): string {
  if (iso === today) return 'Today'
  const t = fromISO(today)
  t.setDate(t.getDate() - 1)
  if (iso === toISO(t)) return 'Yesterday'
  const d = fromISO(iso)
  return d.getFullYear() === fromISO(today).getFullYear() ? dayFmt.format(d) : dayYearFmt.format(d)
}

export function longDate(d = new Date()): string {
  return longFmt.format(d)
}

export function greeting(hour = new Date().getHours()): string {
  if (hour < 5) return 'Good evening'
  if (hour < 12) return 'Good morning'
  if (hour < 17) return 'Good afternoon'
  return 'Good evening'
}
