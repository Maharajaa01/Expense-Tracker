import { expect, tag, test } from './support'

test.describe('Installable PWA and offline sync', () => {
  test('is installable and keeps working offline; changes sync once with conflict handling', async ({ page, context, api, account, categoryId }) => {
    test.slow()
    const title = tag('Offline groceries')
    const editTitle = tag('Edit offline')
    const seed = await api.post('transactions.create', {
      data: { transaction_type: 'Expense', amount: 500, account: account.name, category: await categoryId('Food & Dining'), transaction_date: new Date().toISOString().slice(0, 10), title: editTitle },
      client_txn_id: tag('cid'),
    })

    await page.goto('/expense')
    await page.evaluate(() => navigator.serviceWorker.ready)
    const controlled = await page.evaluate(() => !!navigator.serviceWorker.controller)
    if (!controlled) await page.reload()
    await expect.poll(() => page.evaluate(() => !!navigator.serviceWorker.controller)).toBe(true)

    const cdp = await context.newCDPSession(page)
    const { installabilityErrors } = await cdp.send('Page.getInstallabilityErrors')
    await cdp.detach()
    expect(installabilityErrors).toEqual([])

    // Give the app time to cache recent transactions for offline viewing.
    await page.goto('/expense/transactions')
    await expect(page.getByRole('button', { name: new RegExp(editTitle) })).toBeVisible()
    await page.waitForTimeout(6000)

    await context.setOffline(true)
    await page.reload()
    await expect(page.getByText("You're offline.")).toBeVisible()

    // Offline create
    await page.keyboard.press('n')
    const sheet = page.getByRole('dialog')
    await sheet.getByRole('textbox', { name: 'Amount', exact: true }).fill('77')
    await sheet.getByRole('radio', { name: 'Groceries', exact: true }).click()
    await sheet.getByRole('radiogroup', { name: 'Account', exact: true }).getByRole('radio', { name: new RegExp(account.account_name) }).click()
    await sheet.getByLabel(/Description/).fill(title)
    await page.keyboard.press('Control+Enter')
    await expect(page.getByText(/1 change waiting/)).toBeVisible()
    await expect(page.getByRole('button', { name: new RegExp(title) }).getByLabel('Waiting to sync')).toBeVisible()

    // Offline edit + conflicting edit elsewhere
    await page.getByRole('button', { name: new RegExp(editTitle) }).click()
    await page.getByRole('dialog').getByRole('button', { name: 'Edit' }).click()
    await page.getByRole('dialog').getByRole('textbox', { name: 'Amount', exact: true }).fill('510')
    await page.getByRole('dialog').getByRole('button', { name: /Save changes/ }).click()
    await expect(page.getByText(/2 changes waiting/)).toBeVisible()
    await api.post('transactions.update', { name: seed.transaction.name, data: { amount: 520 } })

    // Back online: sync runs by itself; conflict is surfaced and resolved
    await context.setOffline(false)
    await expect(page.getByText(/needs? your attention/)).toBeVisible({ timeout: 30_000 })
    await page.getByRole('button', { name: 'Review' }).click()
    await page.getByRole('dialog').getByRole('button', { name: 'Keep my version' }).click()
    await expect(page.getByRole('dialog').getByText('Everything is synced.')).toBeVisible({ timeout: 20_000 })

    expect((await api.get('transactions.get', { name: seed.transaction.name })).amount).toBe(510)
    expect((await api.get('transactions.list', { filters: { q: title } })).rows).toHaveLength(1)
  })
})
