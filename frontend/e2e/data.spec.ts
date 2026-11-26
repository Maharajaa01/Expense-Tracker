import fs from 'node:fs'
import path from 'node:path'
import os from 'node:os'
import { fileURLToPath } from 'node:url'
import { request } from '@playwright/test'
import { expect, tag, test } from './support'

const PNG = fileURLToPath(new URL('../../expense_tracker/public/icons/icon-192.png', import.meta.url))

test.describe('Receipts, export and import', () => {
  test('receipts are private to the owner and can be removed', async ({ page, api, account, categoryId }) => {
    const title = tag('Receipt')
    const t = (await api.post('transactions.create', {
      data: { transaction_type: 'Expense', amount: 345, account: account.name, category: await categoryId('Food & Dining'), transaction_date: new Date().toISOString().slice(0, 10), title },
      client_txn_id: tag('cid'),
    })).transaction
    await page.goto(`/expense/transactions?q=${encodeURIComponent(title)}`)
    await page.getByRole('button', { name: new RegExp(title) }).click()
    const sheet = page.getByRole('dialog')
    await sheet.locator('input[type=file]').setInputFiles(PNG)
    await expect(sheet.getByRole('link', { name: /Open icon-192/ })).toBeVisible()

    const [rec] = await api.get('attachments.list', { transaction: t.name })
    expect((await api.raw().get(rec.file_url)).status()).toBe(200)
    // Explicitly empty session: inside the runner, new contexts would otherwise inherit the suite's login.
    const anon = await request.newContext({ baseURL: process.env.ET_BASE_URL, ignoreHTTPSErrors: true, storageState: { cookies: [], origins: [] } })
    expect((await anon.get(rec.file_url, { maxRedirects: 0 })).status()).toBe(403)
    await anon.dispose()

    await sheet.getByRole('button', { name: /Remove icon-192/ }).click()
    await page.getByRole('button', { name: 'Remove', exact: true }).click()
    await expect(sheet.getByText(/No receipt yet/)).toBeVisible()
    expect(await api.get('attachments.list', { transaction: t.name })).toHaveLength(0)
  })

  test('export downloads a CSV; importing the same file twice adds nothing', async ({ page, api, account }) => {
    const label = tag('IMPORT')
    const csv = `Txn Date,Narration,Withdrawal Amt,Deposit Amt\n03/11/2026,${label} CAFE,180.00,\n04/11/2026,${label} REFUND,,250.00\n99/99/2026,${label} BROKEN,10.00,\n`
    const file = path.join(os.tmpdir(), `${label.replace(/\W+/g, '_')}.csv`)
    fs.writeFileSync(file, csv)

    await page.goto('/expense/settings')
    const [download] = await Promise.all([page.waitForEvent('download'), page.getByRole('link', { name: /Export all transactions/ }).click()])
    expect(fs.readFileSync(await download.path(), 'utf8').split('\n')[0]).toContain('Date,Type,Amount,Category')

    for (const round of [1, 2]) {
      await page.getByRole('button', { name: /Import transactions from CSV/ }).click()
      const sheet = page.getByRole('dialog')
      await sheet.locator('input[type=file]').setInputFiles(file)
      await sheet.getByLabel('Account for rows without one').selectOption({ label: account.account_name })
      await sheet.getByRole('button', { name: 'Check file' }).click()
      await expect(sheet.getByText('1 with errors')).toBeVisible()
      if (round === 1) {
        await expect(sheet.getByText('2 ready')).toBeVisible()
        await sheet.getByRole('button', { name: /Import 2 transactions/ }).click()
        await expect(sheet.getByText(/Imported 2\./)).toBeVisible()
        await sheet.getByRole('button', { name: 'Done' }).click()
      } else {
        await expect(sheet.getByText('2 already imported')).toBeVisible()
        await expect(sheet.getByRole('button', { name: 'Nothing to import' })).toBeDisabled()
      }
    }
    const rows = (await api.get('transactions.list', { filters: { q: label } })).rows
    expect(Object.fromEntries(rows.map((r: any) => [r.title.split(' ').pop(), r.transaction_type]))).toEqual({ CAFE: 'Expense', REFUND: 'Income' })
    fs.unlinkSync(file)
  })
})
