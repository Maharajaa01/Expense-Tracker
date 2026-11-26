/** Typed wrappers for the whitelisted Expense Tracker API. */
import { api, ApiError, reportConnectivity } from './api'
import { csrfToken } from './boot'
import type {
  Account, AnalyticsSummary, Budget, BudgetInput, BudgetProgress, Category, DashboardSummary, FinanceNotification, Goal,
  PageMeta, PeriodPreset, Recurring, SortKey, TransactionFilters, TransactionInput, TransactionPage, TransactionRowData,
  UpcomingPayment, Receipt, ImportOptions, ImportPreview, ImportRow, AlertSettings, AlertLogRow, AlertCheckResult,
} from '@/types/finance'

const M = 'expense_tracker.api'

export const transactionsApi = {
  async list(filters: TransactionFilters, page = 1, pageSize = 50, sort: SortKey = 'date_desc') {
    const clean = Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== '' && v != null))
    const env = await api.raw<TransactionPage>('GET', `${M}.transactions.list`, {
      filters: clean, page, page_size: pageSize, sort,
    })
    return { ...env.data, meta: env.meta as PageMeta }
  },
  get: (name: string) => api.get<TransactionRowData>(`${M}.transactions.get`, { name }),
  create: (data: TransactionInput, clientTxnId: string) =>
    api.post<{ transaction: TransactionRowData; duplicate: boolean }>(`${M}.transactions.create`, {
      data, client_txn_id: clientTxnId,
    }),
  update: (name: string, data: Partial<TransactionInput>, expectedModified?: string) =>
    api.post<{ transaction: TransactionRowData }>(`${M}.transactions.update`, {
      name, data, expected_modified: expectedModified,
    }),
  remove: (name: string) => api.post<{ name: string }>(`${M}.transactions.delete`, { name }),
  suggested: (type: 'Expense' | 'Income') =>
    api.get<{ recent: string[]; frequent: string[] }>(`${M}.transactions.suggested_categories`, {
      transaction_type: type,
    }),
}

export interface AccountTotals {
  net_worth: number
  assets: number
  liabilities: number
}

export const accountsApi = {
  async list(includeArchived = true) {
    const env = await api.raw<Account[]>('GET', `${M}.accounts.list`, { include_archived: includeArchived ? 1 : 0 })
    return { accounts: env.data, totals: env.meta as AccountTotals }
  },
  create: (data: Partial<Account>) => api.post<Account>(`${M}.accounts.create`, { data }),
  update: (name: string, data: Partial<Account>) => api.post<Account>(`${M}.accounts.update`, { name, data }),
  setArchived: (name: string, archived: boolean) =>
    api.post<Account>(`${M}.accounts.set_archived`, { name, archived: archived ? 1 : 0 }),
  remove: (name: string) => api.post<{ name: string }>(`${M}.accounts.delete`, { name }),
}

export const categoriesApi = {
  list: (includeArchived = true) =>
    api.get<Category[]>(`${M}.categories.list`, { include_archived: includeArchived ? 1 : 0 }),
  create: (data: Partial<Category>) => api.post<Category>(`${M}.categories.create`, { data }),
  update: (name: string, data: Partial<Category>) => api.post<Category>(`${M}.categories.update`, { name, data }),
  setArchived: (name: string, archived: boolean) =>
    api.post<Category>(`${M}.categories.set_archived`, { name, archived: archived ? 1 : 0 }),
  remove: (name: string) => api.post<{ name: string }>(`${M}.categories.delete`, { name }),
}

export const dashboardApi = {
  summary: (preset: PeriodPreset, fromDate?: string, toDate?: string) =>
    api.get<DashboardSummary>(`${M}.dashboard.summary`, { preset, from_date: fromDate, to_date: toDate }),
}

export const profileApi = {
  update: (data: { theme?: 'System' | 'Light' | 'Dark'; week_start?: 'Monday' | 'Sunday'; default_account?: string }) =>
    api.post<Record<string, string>>(`${M}.profile.update`, { data }),
}

export const budgetsApi = {
  list: (month?: string, includeInactive = true) =>
    api.get<Budget[]>(`${M}.budgets.list`, { month, include_inactive: includeInactive ? 1 : 0 }),
  history: (name: string, months = 6) =>
    api.get<{ budget: Budget; history: (BudgetProgress & { month: string })[] }>(`${M}.budgets.history`, { name, months }),
  create: (data: BudgetInput) => api.post<Budget>(`${M}.budgets.create`, { data }),
  update: (name: string, data: Partial<BudgetInput>) => api.post<Budget>(`${M}.budgets.update`, { name, data }),
  remove: (name: string) => api.post<{ name: string }>(`${M}.budgets.delete`, { name }),
}

export const analyticsApi = {
  summary: (preset: PeriodPreset, fromDate?: string, toDate?: string) =>
    api.get<AnalyticsSummary>(`${M}.analytics.summary`, { preset, from_date: fromDate, to_date: toDate }),
}

export const recurringApi = {
  list: () => api.get<Recurring[]>(`${M}.recurring.list`),
  upcoming: (days = 30) => api.get<UpcomingPayment[]>(`${M}.recurring.upcoming`, { days }),
  create: (data: Partial<Recurring>) => api.post<Recurring>(`${M}.recurring.create`, { data }),
  update: (name: string, data: Partial<Recurring>) => api.post<Recurring>(`${M}.recurring.update`, { name, data }),
  postNow: (name: string) =>
    api.post<{ recurring: Recurring; transaction: TransactionRowData }>(`${M}.recurring.post_now`, { name }),
  skipNext: (name: string) => api.post<Recurring>(`${M}.recurring.skip_next`, { name }),
  remove: (name: string) => api.post<{ name: string }>(`${M}.recurring.delete`, { name }),
}

export const goalsApi = {
  list: (includeArchived = false) => api.get<Goal[]>(`${M}.goals.list`, { include_archived: includeArchived ? 1 : 0 }),
  create: (data: Partial<Goal>) => api.post<Goal>(`${M}.goals.create`, { data }),
  update: (name: string, data: Partial<Goal>) => api.post<Goal>(`${M}.goals.update`, { name, data }),
  contribute: (name: string, args: { amount: number; kind: 'Contribution' | 'Withdrawal'; date: string; source_account?: string | null; note?: string | null }) =>
    api.post<Goal>(`${M}.goals.contribute`, { name, ...args }),
  removeContribution: (name: string, row: string) => api.post<Goal>(`${M}.goals.remove_contribution`, { name, row }),
  remove: (name: string) => api.post<{ name: string }>(`${M}.goals.delete`, { name }),
}

export const notificationsApi = {
  async list(unreadOnly = false, limit = 30) {
    const env = await api.raw<FinanceNotification[]>('GET', `${M}.notifications.list`, { unread_only: unreadOnly ? 1 : 0, limit })
    return { items: env.data, unread: (env.meta?.unread as number) ?? 0 }
  },
  markRead: (name?: string) =>
    api.post<{ unread: number }>(`${M}.notifications.mark_read`, name ? { name } : { all: 1 }),
}

export const MAX_RECEIPT_MB = 10

export const attachmentsApi = {
  list: (transaction: string) => api.get<Receipt[]>(`${M}.attachments.list`, { transaction }),
  remove: (name: string) => api.post<{ name: string }>(`${M}.attachments.delete`, { name }),
  /** Multipart upload (not JSON), so it uses fetch directly with the session's CSRF token. */
  async upload(transaction: string, file: File): Promise<Receipt> {
    if (file.size > MAX_RECEIPT_MB * 1024 * 1024) throw new ApiError('validation', `Receipts can be at most ${MAX_RECEIPT_MB} MB.`)
    const form = new FormData()
    form.append('transaction', transaction)
    form.append('file', file, file.name)
    let res: Response
    try {
      res = await fetch(`/api/method/${M}.attachments.upload`, {
        method: 'POST', body: form, credentials: 'same-origin',
        headers: { 'X-Frappe-CSRF-Token': csrfToken(), Accept: 'application/json' },
      })
    } catch {
      reportConnectivity(false)
      throw new ApiError('network', 'You appear to be offline.')
    }
    const body = await res.json().catch(() => null)
    if (!res.ok || !body?.message?.ok) {
      let msg = 'Could not upload the receipt.'
      try {
        msg = JSON.parse(JSON.parse(body._server_messages)[0]).message.replace(/<[^>]*>/g, '')
      } catch {
        /* keep generic */
      }
      throw new ApiError(res.status === 403 ? 'permission' : 'validation', msg, res.status)
    }
    return body.message.data
  },
}

export const ioApi = {
  /** URL that downloads the CSV for these filters (GET with the session cookie). */
  exportUrl(filters: TransactionFilters = {}) {
    const clean = Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== '' && v != null))
    return `/api/method/${M}.io.export_csv?filters=${encodeURIComponent(JSON.stringify(clean))}`
  },
  preview: (text: string, options: ImportOptions) => api.post<ImportPreview>(`${M}.io.preview_import`, { text, options }),
  commit: (text: string, options: ImportOptions) =>
    api.post<{ imported: number; skipped: number; failed: number; rows: ImportRow[] }>(`${M}.io.commit_import`, { text, options }),
}

export const alertsApi = {
  settings: () => api.get<AlertSettings>(`${M}.alerts.get_settings`),
  save: (data: { email?: string; app_password?: string; since?: string; enabled?: 0 | 1 }) =>
    api.post<AlertSettings>(`${M}.alerts.save_settings`, { data }),
  test: () => api.post<{ ok: boolean; error?: string; messages?: number; bank_messages?: number }>(`${M}.alerts.test_connection`, {}),
  checkNow: () => api.post<AlertCheckResult>(`${M}.alerts.check_now`, {}),
  log: (limit = 30) => api.get<AlertLogRow[]>(`${M}.alerts.log`, { limit }),
}
