import { test as base, expect, request, type APIRequestContext } from '@playwright/test'

/** Thin API client for fixtures and assertions (same session as the browser). */
export class Api {
  constructor(private ctx: APIRequestContext, private csrf: string) {}

  static async create(): Promise<Api> {
    const ctx = await request.newContext({ baseURL: process.env.ET_BASE_URL, ignoreHTTPSErrors: true, storageState: 'e2e/.auth/state.json' })
    const boot = await (await ctx.get('/api/method/expense_tracker.api.boot.get_boot')).json()
    return new Api(ctx, boot.message.data.csrf_token)
  }

  async get<T = any>(method: string, params: Record<string, unknown> = {}): Promise<T> {
    const qs = new URLSearchParams(Object.entries(params).map(([k, v]) => [k, typeof v === 'object' ? JSON.stringify(v) : String(v)]))
    const res = await this.ctx.get(`/api/method/expense_tracker.api.${method}?${qs}`)
    const body = await res.json()
    if (!res.ok()) throw new Error(`${method}: ${res.status()} ${JSON.stringify(body).slice(0, 300)}`)
    return body.message.data
  }

  async post<T = any>(method: string, data: Record<string, unknown>): Promise<T> {
    const res = await this.ctx.post(`/api/method/expense_tracker.api.${method}`, { data, headers: { 'X-Frappe-CSRF-Token': this.csrf } })
    const body = await res.json()
    if (!res.ok()) throw new Error(`${method}: ${res.status()} ${JSON.stringify(body).slice(0, 300)}`)
    return body.message.data
  }

  raw() {
    return this.ctx
  }
}

/** Unique tag per test so data never collides with real records or other runs. */
export function tag(prefix = 'E2E') {
  return `${prefix} ${Date.now().toString(36)}${Math.random().toString(36).slice(2, 5)}`
}

interface Fixtures {
  api: Api
  /** A fresh account for this test (deleted afterwards with everything posted to it). */
  account: { name: string; account_name: string }
  categoryId: (name: string, type?: 'Expense' | 'Income') => Promise<string>
}

export const test = base.extend<Fixtures>({
  api: async ({}, use) => {
    await use(await Api.create())
  },
  account: async ({ api }, use) => {
    const acc = await api.post('accounts.create', { data: { account_name: tag('E2E Bank'), account_type: 'Savings Account', opening_balance: 10000 } })
    await use(acc)
    // Cleanup: transactions on the account, then the account itself.
    for (let page = 0; page < 20; page++) {
      const rows = (await api.get('transactions.list', { filters: { account: acc.name }, page_size: 100 })).rows
      if (!rows.length) break
      for (const r of rows) await api.post('transactions.delete', { name: r.name }).catch(() => {})
    }
    await api.post('accounts.delete', { name: acc.name }).catch(() => api.post('accounts.set_archived', { name: acc.name, archived: 1 }))
  },
  categoryId: async ({ api }, use) => {
    const cats: any[] = await api.get('categories.list')
    await use(async (name, type = 'Expense') => {
      const c = cats.find((x) => x.category_name === name && x.category_type === type)
      if (!c) throw new Error(`Default category ${name} missing for the test user`)
      return c.name
    })
  },
})

export { expect }
