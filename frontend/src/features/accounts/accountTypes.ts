import type { AccountType } from '@/types/finance'

export const ACCOUNT_TYPES: { value: AccountType; label: string; icon: string; color: string }[] = [
  { value: 'Cash', label: 'Cash', icon: 'wallet', color: '#10b981' },
  { value: 'Savings Account', label: 'Savings', icon: 'piggy-bank', color: '#0d9488' },
  { value: 'Current Account', label: 'Current', icon: 'landmark', color: '#3b82f6' },
  { value: 'Credit Card', label: 'Credit card', icon: 'credit-card', color: '#7c3aed' },
  { value: 'Digital Wallet', label: 'Wallet / UPI', icon: 'smartphone', color: '#f59e0b' },
  { value: 'Other', label: 'Other', icon: 'coins', color: '#64748b' },
]
