import { expect, test } from './support'

const PAGES = ['', '/transactions', '/budgets', '/accounts', '/categories', '/analytics', '/recurring', '/goals', '/settings', '/profile']

test.describe('Mobile layout', () => {
  for (const p of PAGES) {
    test(`${p || '/'} fits the screen`, async ({ page }) => {
      await page.goto(`/expense${p}`)
      await page.waitForLoadState('networkidle')
      await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
      const width = await page.evaluate(() => document.documentElement.scrollWidth)
      expect(width).toBeLessThanOrEqual(page.viewportSize()!.width)
    })
  }

  test('the Add button opens Quick Add as a bottom sheet', async ({ page }) => {
    await page.goto('/expense')
    await page.getByRole('navigation', { name: 'Main' }).getByRole('button', { name: 'Add transaction' }).click()
    await expect(page.getByRole('textbox', { name: 'Amount', exact: true })).toBeVisible()
  })

  test('shows an Install button until the app is installed', async ({ page }) => {
    await page.goto('/expense')
    const banner = page.getByText('Install the app')
    const installed = await page.evaluate(() => localStorage.getItem('et-installed') === '1')
    if (installed) await expect(banner).toBeHidden()
    else await expect(banner).toBeVisible()
  })
})
