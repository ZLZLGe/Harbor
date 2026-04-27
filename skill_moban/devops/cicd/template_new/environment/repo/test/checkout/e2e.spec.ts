import { expect, test } from '@playwright/test'

test('checkout applies saved shipping method after address edit', async ({ page }) => {
  await page.goto('/checkout')
  await page.getByLabel('Street address').fill('901 Market Street')
  await page.getByRole('button', { name: 'Save address' }).click()

  // This assertion is timing-prone in the production bundle because the
  // shipping method label is populated after an async persisted-cart refresh.
  await expect(page.getByTestId('shipping-method-label')).toHaveText(/Standard shipping/, { timeout: 5000 })
})
