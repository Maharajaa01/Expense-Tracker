/** Budget-style tone by utilisation: alerts at 50/80/100 (docs/ACCOUNTING.md). */
export type ProgressTone = 'brand' | 'warn' | 'expense' | 'savings' | 'accent'

export function toneForUtilisation(percent: number): ProgressTone {
  if (percent >= 100) return 'expense'
  if (percent >= 80) return 'warn'
  return 'brand'
}

export function clampPercent(p: number | null | undefined): number {
  if (p == null || !Number.isFinite(p)) return 0
  return Math.min(Math.max(p, 0), 100)
}
