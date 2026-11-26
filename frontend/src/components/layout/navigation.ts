export interface NavItem {
  name: string // route name
  label: string
  icon: string
}

/** Desktop sidebar, in the order from the product brief. */
export const SIDEBAR: NavItem[] = [
  { name: 'dashboard', label: 'Dashboard', icon: 'layout-dashboard' },
  { name: 'transactions', label: 'Transactions', icon: 'arrow-left-right' },
  { name: 'budgets', label: 'Budgets', icon: 'chart-pie' },
  { name: 'accounts', label: 'Accounts', icon: 'wallet' },
  { name: 'categories', label: 'Categories', icon: 'tags' },
  { name: 'analytics', label: 'Analytics', icon: 'chart-column' },
  { name: 'recurring', label: 'Recurring payments', icon: 'calendar-sync' },
  { name: 'goals', label: 'Savings goals', icon: 'piggy-bank' },
  { name: 'settings', label: 'Settings', icon: 'settings' },
]

/** Mobile bottom bar: Home, Transactions, [Add], Budgets, Profile. */
export const BOTTOM_LEFT: NavItem[] = [
  { name: 'dashboard', label: 'Home', icon: 'house' },
  { name: 'transactions', label: 'Transactions', icon: 'arrow-left-right' },
]
export const BOTTOM_RIGHT: NavItem[] = [
  { name: 'budgets', label: 'Budgets', icon: 'chart-pie' },
  { name: 'profile', label: 'Profile', icon: 'user' },
]

/** Pages reached from the Profile tab on mobile (not in the bottom bar). */
export const PROFILE_LINKS: NavItem[] = SIDEBAR.filter(
  (i) => !['dashboard', 'transactions', 'budgets'].includes(i.name),
)
