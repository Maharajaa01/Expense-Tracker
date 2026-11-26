export type TransactionType = 'Expense' | 'Income' | 'Transfer'
export type AccountType = 'Cash' | 'Savings Account' | 'Current Account' | 'Credit Card' | 'Digital Wallet' | 'Other'

/** Row shape returned by the transactions list API. */
export interface TransactionRowData {
  name: string
  transaction_type: TransactionType
  transaction_date: string
  amount: number
  is_refund: 0 | 1
  title: string
  notes?: string | null
  account: string
  account_name: string
  to_account?: string | null
  to_account_name?: string | null
  category?: string | null
  category_name?: string | null
  category_icon?: string | null
  category_color?: string | null
  parent_category?: string | null
  has_attachments?: 0 | 1
  source?: string
  savings_goal?: string | null
  client_txn_id?: string
  modified?: string
  /** Present for rows created offline and not yet synced. */
  pending?: boolean
  /** Created automatically (bank alert) and waiting for a category. */
  needs_review?: 0 | 1
  bank_reference?: string | null
}

export interface Account {
  name: string
  account_name: string
  account_type: AccountType
  account_last4?: string | null
  opening_balance: number
  opening_date: string | null
  balance: number
  credit_limit: number
  available_credit?: number
  icon: string
  color: string
  include_in_totals: 0 | 1
  is_archived: 0 | 1
  notes: string | null
  sort_order: number
  has_transactions: boolean
  modified: string
}

export interface Category {
  name: string
  category_name: string
  category_type: 'Expense' | 'Income'
  parent_category: string | null
  icon: string
  color: string
  is_default: 0 | 1
  is_archived: 0 | 1
  sort_order: number
  txn_count: number
  modified: string
}

export interface TransactionInput {
  transaction_type: TransactionType
  amount: number
  transaction_date: string
  account: string
  to_account?: string | null
  category?: string | null
  title?: string | null
  notes?: string | null
  is_refund?: 0 | 1
}

export interface TransactionFilters {
  type?: TransactionType | ''
  account?: string
  category?: string
  from_date?: string
  to_date?: string
  q?: string
  needs_review?: 0 | 1
}

export type SortKey = 'date_desc' | 'date_asc' | 'amount_desc' | 'amount_asc'

export interface DayTotals {
  income: number
  expense: number
}

export interface TransactionPage {
  rows: TransactionRowData[]
  day_totals: Record<string, DayTotals>
  summary?: { income: number; expense: number }
}

export interface PageMeta {
  page: number
  page_size: number
  has_more: boolean
  total?: number
}

export type PeriodPreset = 'today' | 'this_week' | 'this_month' | 'last_month' | 'this_quarter' | 'this_year' | 'custom'

export interface Totals {
  income: number
  expense: number
  savings: number
  savings_rate: number | null
}

export interface CategoryTotal {
  category: string
  category_name: string
  icon: string
  color: string
  amount: number
  count: number
  share: number | null
}

export interface SeriesPoint {
  period: string
  income: number
  expense: number
}

export interface DashboardSummary {
  period: { preset: PeriodPreset; from_date: string; to_date: string; prev_from_date: string; prev_to_date: string; days: number }
  totals: Totals
  previous: Totals
  /** % change vs the previous period; null when there is no base to compare. */
  change: { income: number | null; expense: number | null }
  net_worth: {
    total: number
    account_count: number
    accounts: { name: string; account_name: string; account_type: AccountType; balance: number; icon: string; color: string }[]
  }
  categories: CategoryTotal[]
  trend: { granularity: 'day' | 'week' | 'month'; points: SeriesPoint[] }
  monthly: SeriesPoint[]
  recent: TransactionRowData[]
  budget_alerts: Budget[]
  budgets_count: number
  to_categorise: number
  upcoming: UpcomingPayment[]
  goals: Goal[]
  insights: Insight[]
}

// ----- Phase 5 -------------------------------------------------------------------
export type BudgetLevel = 'ok' | '50' | '80' | '100' | 'over'

export interface BudgetProgress {
  from_date: string
  to_date: string
  amount: number
  carried: number
  available: number
  spent: number
  remaining: number
  percent: number | null
  level: BudgetLevel
}

export interface Budget {
  name: string
  budget_name: string
  category: string | null
  category_name: string | null
  icon: string
  color: string
  amount?: number
  period_type: 'Monthly' | 'Custom'
  start_date: string
  end_date: string | null
  carry_forward: 0 | 1
  is_active: 0 | 1
  alert_50: 0 | 1
  alert_80: 0 | 1
  alert_100: 0 | 1
  modified: string
  progress: BudgetProgress | null
}

export interface BudgetInput {
  budget_name: string
  category: string | null
  amount: number
  period_type: 'Monthly' | 'Custom'
  start_date: string
  end_date: string | null
  carry_forward: 0 | 1
  is_active: 0 | 1
  alert_50: 0 | 1
  alert_80: 0 | 1
  alert_100: 0 | 1
}

export type Frequency = 'Daily' | 'Weekly' | 'Monthly' | 'Quarterly' | 'Yearly' | 'Custom'

export interface Recurring {
  name: string
  title: string
  transaction_type: TransactionType
  amount: number
  account: string
  account_name?: string
  to_account: string | null
  to_account_name?: string
  category: string | null
  category_name?: string
  category_icon: string | null
  category_color: string | null
  notes: string | null
  frequency: Frequency
  interval: number
  custom_unit: 'Days' | 'Weeks' | 'Months' | null
  start_date: string
  end_date: string | null
  next_run_date: string | null
  last_run_date: string | null
  occurrences_posted: number
  auto_post: 0 | 1
  remind_days_before: number
  is_active: 0 | 1
  schedule: string
  modified: string
}

export interface UpcomingPayment {
  recurring: string
  title: string
  transaction_type: TransactionType
  amount: number
  date: string
  overdue: boolean
  auto_post: 0 | 1
  category: string | null
  account: string
}

export interface GoalContribution {
  name: string
  date: string
  kind: 'Contribution' | 'Withdrawal'
  amount: number
  source_account: string | null
  transaction: string | null
  note: string | null
}

export interface Goal {
  name: string
  goal_name: string
  target_amount: number
  current_amount: number
  remaining: number
  percent: number | null
  start_date: string | null
  target_date: string | null
  days_left: number | null
  monthly_needed: number | null
  linked_account: string | null
  linked_account_name: string | null
  icon: string
  color: string
  status: 'Active' | 'Achieved' | 'Archived'
  modified: string
  contributions: GoalContribution[]
}

export interface Insight {
  kind: string
  tone: 'good' | 'warning' | 'neutral'
  icon: string
  text: string
}

export interface CategoryComparisonRow {
  category: string
  category_name: string
  icon: string
  color: string
  current: number
  previous: number
  change: number | null
}

export interface SavingsPoint extends SeriesPoint {
  savings: number
  rate: number | null
}

export interface AnalyticsSummary {
  period: DashboardSummary['period']
  totals: Totals
  previous: Totals
  change: { income: number | null; expense: number | null }
  categories: CategoryTotal[]
  income_categories: CategoryTotal[]
  comparison: CategoryComparisonRow[]
  trend: { granularity: 'day' | 'week' | 'month'; points: SeriesPoint[] }
  daily: SeriesPoint[] | null
  monthly: SeriesPoint[]
  savings: SavingsPoint[]
  budgets: Budget[]
  insights: Insight[]
}

export interface FinanceNotification {
  name: string
  notification_type: 'Budget' | 'Recurring' | 'Goal' | 'Sync' | 'System'
  severity: 'Info' | 'Success' | 'Warning' | 'Danger'
  title: string
  message: string | null
  reference_doctype: string | null
  reference_name: string | null
  is_read: 0 | 1
  creation: string
}

// ----- Phase 7 -------------------------------------------------------------------
export interface Receipt {
  name: string
  transaction: string
  file_name: string
  file_url: string
  mime_type: string
  file_size: number
  ocr_status: 'Not Processed' | 'Queued' | 'Done' | 'Failed'
  extracted_data: Record<string, unknown> | null
  creation: string
}

export interface ImportRow {
  row: number
  client_txn_id: string
  transaction_date: string
  transaction_type: TransactionType
  amount: number | null
  account: string | null
  to_account: string | null
  category: string | null
  title: string | null
  notes: string | null
  is_refund: 0 | 1
  errors: string[]
  status: 'ok' | 'error' | 'duplicate' | 'imported'
}

export interface ImportPreview {
  columns: Record<string, string>
  rows: ImportRow[]
  new_categories: { type: string; name: string }[]
  summary: { ok: number; error: number; duplicate: number; imported: number }
}

export interface ImportOptions {
  default_account?: string
  default_type?: 'Expense' | 'Income'
  create_missing_categories?: 0 | 1
  include_duplicates?: 0 | 1
}

// ----- Bank alert emails ---------------------------------------------------------
export interface AlertSettings {
  enabled: 0 | 1
  email: string | null
  has_password: boolean
  since: string | null
  last_checked: string | null
  last_error: string | null
  accounts_without_digits: string[]
}

export interface AlertLogRow {
  name: string
  received_on: string | null
  bank: string | null
  status: 'Posted' | 'Duplicate' | 'Unrecognised' | 'Needs Account' | 'Ignored' | 'Failed'
  transaction_type: 'Expense' | 'Income' | null
  amount: number
  account_last4: string | null
  reference: string | null
  merchant: string | null
  transaction: string | null
  note: string | null
  snippet: string | null
}

export interface AlertCheckResult {
  ok: boolean
  error?: string
  checked?: number
  results?: Record<string, number>
}
