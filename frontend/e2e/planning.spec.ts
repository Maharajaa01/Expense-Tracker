import { expect, tag, test } from './support'

test.describe('Budgets and savings goals', () => {
  test('an exceeded budget shows as over and raises one alert', async ({ page, api, account, categoryId }) => {
    const budgets: any[] = await api.get('budgets.list')
    test.skip(budgets.some((b) => b.category && b.is_active && b.category_name === 'Personal Care'), 'test user already has a Personal Care budget')
    const cat = await categoryId('Personal Care')
    const first = new Date(); first.setDate(1)
    const b = await api.post('budgets.create', { data: { budget_name: tag('Care'), category: cat, amount: 100, start_date: first.toISOString().slice(0, 10) } })
    try {
      await api.post('transactions.create', { data: { transaction_type: 'Expense', amount: 150, account: account.name, category: cat, transaction_date: new Date().toISOString().slice(0, 10) }, client_txn_id: tag('b') })
      await page.goto('/expense/budgets')
      const card = page.getByRole('button', { name: new RegExp(b.budget_name) })
      await expect(card.getByText('Over budget')).toBeVisible()
      await expect(card.getByText('over', { exact: true })).toBeVisible()
      const notes: any[] = await api.get('notifications.list')
      expect(notes.filter((n) => n.title.startsWith(b.budget_name) && /over budget/.test(n.title))).toHaveLength(1)
    } finally {
      await api.post('budgets.delete', { name: b.name })
    }
  })

  test('adding to a goal linked to an account moves money as a transfer', async ({ page, api, account }) => {
    const vault = await api.post('accounts.create', { data: { account_name: tag('E2E Vault'), account_type: 'Savings Account' } })
    const g = await api.post('goals.create', { data: { goal_name: tag('Bike'), target_amount: 60000, linked_account: vault.name } })
    try {
      await page.goto('/expense/goals')
      const card = page.locator('article', { hasText: g.goal_name })
      await card.getByRole('button', { name: 'Add money' }).click()
      const sheet = page.getByRole('dialog')
      await sheet.getByRole('textbox', { name: 'Amount', exact: true }).fill('2000')
      await sheet.getByLabel('From account').selectOption({ label: account.account_name })
      await sheet.getByRole('button', { name: 'Add money' }).click()
      await expect(page.getByText(new RegExp(`2,000.00 added to ${g.goal_name}`))).toBeVisible()
      expect((await api.get('accounts.get', { name: account.name })).balance).toBe(8000)
      expect((await api.get('accounts.get', { name: vault.name })).balance).toBe(2000)
    } finally {
      const goal = (await api.get('goals.list', { include_archived: 1 })).find((x: any) => x.name === g.name)
      for (const c of goal?.contributions ?? []) await api.post('goals.remove_contribution', { name: g.name, row: c.name })
      await api.post('goals.delete', { name: g.name })
      await api.post('accounts.delete', { name: vault.name })
    }
  })
})
