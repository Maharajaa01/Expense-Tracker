import { request, type FullConfig } from '@playwright/test'
import fs from 'node:fs'

/** Log in once and save the session for all tests. */
export default async function globalSetup(_config: FullConfig) {
  const base = process.env.ET_BASE_URL
  const usr = process.env.ET_USER
  const pwd = process.env.ET_PASSWORD
  if (!base || !usr || !pwd) throw new Error('Set ET_BASE_URL, ET_USER and ET_PASSWORD (see playwright.config.ts).')
  const ctx = await request.newContext({ baseURL: base, ignoreHTTPSErrors: true })
  const res = await ctx.post('/api/method/login', { form: { usr, pwd } })
  if (!res.ok()) throw new Error(`Login failed for ${usr}: HTTP ${res.status()}`)
  const boot = await ctx.get('/api/method/expense_tracker.api.boot.get_boot')
  if (!boot.ok()) throw new Error(`${usr} cannot open Expense Tracker (does the user have the "Expense User" role?)`)
  fs.mkdirSync('e2e/.auth', { recursive: true })
  await ctx.storageState({ path: 'e2e/.auth/state.json' })
  await ctx.dispose()
}
