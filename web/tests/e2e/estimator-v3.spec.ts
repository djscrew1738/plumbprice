import { test, expect } from '@playwright/test'

test.describe('Estimator v3', () => {
  test('estimator page loads with v3 chat UI', async ({ page }) => {
    await page.goto('/estimator')
    await expect(page).toHaveURL(/\/estimator/)
    await expect(page.locator('body')).toBeVisible()

    const chatInput = page.locator('textarea[aria-label="Type a pricing question"]')
    await expect(chatInput).toBeVisible()

    const sendButton = page.locator('button[aria-label="Send message"]')
    await expect(sendButton).toBeVisible()
  })

  test('suggestion chips are visible', async ({ page }) => {
    await page.goto('/estimator')

    const suggestions = page.locator('button[type="button"]').filter({ hasText: /Kitchen sink|Water heater|house repipe/i })
    await expect(suggestions.first()).toBeVisible()
  })

  test('send button is disabled when input is empty', async ({ page }) => {
    await page.goto('/estimator')
    await page.waitForLoadState('networkidle')

    const sendButton = page.locator('button[aria-label="Send message"]')
    await expect(sendButton).toBeDisabled()
  })

  test('clicking a suggestion chip sends a message to chat', async ({ page }) => {
    await page.goto('/estimator')
    await page.waitForLoadState('networkidle')

    // Click a suggestion chip (uses actual chip text from EstimatorPageV3)
    const chip = page.locator('button').filter({ hasText: 'Kitchen sink rough-in, 2 fixtures' }).first()
    await expect(chip).toBeVisible()
    await chip.click()

    // The user message should appear immediately in the chat list
    await expect(page.locator('text=Kitchen sink rough-in').first()).toBeVisible({ timeout: 6000 })
  })
})
