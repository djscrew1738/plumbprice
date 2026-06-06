import { test, expect } from '@playwright/test'

test.describe('Blueprint v3', () => {
  test('blueprints page loads', async ({ page }) => {
    await page.goto('/blueprints')
    await expect(page).toHaveURL(/\/blueprints/)
    await expect(page.locator('body')).toBeVisible()
  })

  test('upload drop zone is visible', async ({ page }) => {
    await page.goto('/blueprints')

    // Actual aria-label from BlueprintsPage.tsx
    const dropZone = page.locator('[role="button"][aria-label*="Upload blueprint files"]')
    await expect(dropZone).toBeVisible()
  })

  test('upload drop zone is keyboard focusable', async ({ page }) => {
    await page.goto('/blueprints')

    const dropZone = page.locator('[role="button"][aria-label*="Upload blueprint files"]')
    await dropZone.focus()
    await expect(dropZone).toBeFocused()
  })

  test('estimator page loads with chat input', async ({ page }) => {
    await page.goto('/estimator')

    const chatInput = page.locator('textarea[aria-label="Type a pricing question"]')
    await expect(chatInput).toBeVisible()
  })
})
