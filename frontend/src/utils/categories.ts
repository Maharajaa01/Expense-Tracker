import type { Category } from '@/types/finance'

/** System categories that hold bank-alert entries until the user picks a real one. */
export const UNCATEGORISED_NAMES = ['Uncategorised', 'Uncategorised income']

export const isUncategorised = (c: Pick<Category, 'category_name' | 'is_default'>) =>
  !!c.is_default && UNCATEGORISED_NAMES.includes(c.category_name)
