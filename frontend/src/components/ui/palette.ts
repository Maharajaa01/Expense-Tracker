import iconSet from '@/theme/icon-set.json'

/** Colours offered for categories, accounts and goals. Mid-tone so they read on light and dark. */
export const SWATCHES = [
  '#10b981', '#16a34a', '#84cc16', '#eab308', '#f59e0b', '#f97316', '#ef4444', '#e5484d',
  '#ec4899', '#d946ef', '#a855f7', '#7c3aed', '#6366f1', '#3b82f6', '#0ea5e9', '#06b6d4',
  '#14b8a6', '#0d9488', '#64748b', '#94a3b8',
]

export const ICONS = iconSet as Record<'category' | 'account' | 'goal' | 'ui', string[]>
