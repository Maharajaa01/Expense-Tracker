import { expect, tag, test } from './support'

test.describe('Quick Add, edit, delete and balances', () => {
  test('records an expense from the keyboard in one pass and updates the balance', async ({ page, api, account }) => {
    const title = tag('Lunch')
    await page.goto('/expense')
    await page.keyboard.press('n')
    const sheet = page.getByRole('dialog')
    await expect(sheet.getByRole('textbox', { name: 'Amount', exact: true })).toBeFocused()
    await sheet.getByRole('textbox', { name: 'Amount', exact: true }).fill('450')
    await sheet.getByRole('radio', { name: 'Food & Dining', exact: true }).click()
    await sheet.getByRole('radiogroup', { name: 'Account', exact: true }).getByRole('radio', { name: new RegExp(account.account_name) }).click()
    await sheet.getByLabel(/Description/).fill(title)
    await page.keyboard.press('Control+Enter')
    await expect(sheet).toBeHidden()
    await expect(page.getByText(/Expense of ₹450\.00 saved/)).toBeVisible()

    const acc = await api.get('accounts.get', { name: account.name })
    expect(acc.balance).toBe(9550)
  })

  test('a double-click on Save records only one transaction', async ({ page, api, account }) => {
    const title = tag('Double')
    await page.goto('/expense')
    await page.getByRole('button', { name: /Add transaction/ }).first().click()
    const sheet = page.getByRole('dialog')
    await sheet.getByRole('textbox', { name: 'Amount', exact: true }).fill('99')
    await sheet.getByRole('radio', { name: 'Groceries', exact: true }).click()
    await sheet.getByRole('radiogroup', { name: 'Account', exact: true }).getByRole('radio', { name: new RegExp(account.account_name) }).click()
    await sheet.getByLabel(/Description/).fill(title)
    await sheet.getByRole('button', { name: /Save expense/ }).dblclick()
    await expect(sheet).toBeHidden()
    const rows = (await api.get('transactions.list', { filters: { q: title } })).rows
    expect(rows).toHaveLength(1)
  })

  test('edit and delete recalculate the balance', async ({ page, api, account, categoryId }) => {
    const title = tag('Edit me')
    await api.post('transactions.create', {
      data: { transaction_type: 'Expense', amount: 100, account: account.name, category: await categoryId('Food & Dining'), transaction_date: new Date().toISOString().slice(0, 10), title },
      client_txn_id: tag('cid'),
    })
    await page.goto(`/expense/transactions?q=${encodeURIComponent(title)}`)
    await page.getByRole('button', { name: new RegExp(title) }).click()
    await page.getByRole('dialog').getByRole('button', { name: 'Edit' }).click()
    await page.getByRole('dialog').getByRole('textbox', { name: 'Amount', exact: true }).fill('250')
    await page.getByRole('dialog').getByRole('button', { name: /Save changes/ }).click()
    await expect(page.getByText('Expense updated')).toBeVisible()
    expect((await api.get('accounts.get', { name: account.name })).balance).toBe(9750)

    await page.getByRole('button', { name: new RegExp(title) }).click()
    await page.getByRole('dialog').getByRole('button', { name: 'Delete' }).click()
    await page.getByRole('button', { name: 'Delete', exact: true }).last().click()
    await expect(page.getByText('Transaction deleted')).toBeVisible()
    expect((await api.get('accounts.get', { name: account.name })).balance).toBe(10000)
  })

  test('a credit card bill payment is a transfer, not spending', async ({ api, account, categoryId }) => {
    const card = await api.post('accounts.create', { data: { account_name: tag('E2E Card'), account_type: 'Credit Card', credit_limit: 50000 } })
    try {
      const today = new Date().toISOString().slice(0, 10)
      await api.post('transactions.create', { data: { transaction_type: 'Expense', amount: 3000, account: card.name, category: await categoryId('Shopping'), transaction_date: today }, client_txn_id: tag('c1') })
      await api.post('transactions.create', { data: { transaction_type: 'Transfer', amount: 3000, account: account.name, to_account: card.name, transaction_date: today }, client_txn_id: tag('c2') })
      expect((await api.get('accounts.get', { name: card.name })).balance).toBe(0)
      expect((await api.get('accounts.get', { name: account.name })).balance).toBe(7000)
      const spent = (await api.get('transactions.list', { filters: { account: card.name, type: 'Expense' } })).summary.expense
      expect(spent).toBe(3000) // counted once
    } finally {
      for (const r of (await api.get('transactions.list', { filters: { account: card.name } })).rows) await api.post('transactions.delete', { name: r.name })
      await api.post('accounts.delete', { name: card.name })
    }
  })
})
