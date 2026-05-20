import { test, expect } from '@playwright/test'

test.describe('Estimator v3', () => {
  test('estimator page loads with v3 chat UI', async ({ page }) => {
    await page.goto('/estimator')
    await expect(page).toHaveURL(/\/estimator/)
    await expect(page.locator('body')).toBeVisible()

    // Chat input should be present
    const chatInput = page.locator('textarea[aria-label="Type a pricing question"]')
    await expect(chatInput).toBeVisible()

    // Send button should be present
    const sendButton = page.locator('button[aria-label="Send message"]')
    await expect(sendButton).toBeVisible()

    // Blueprint image upload button should be present
    const uploadButton = page.locator('button[aria-label="Attach blueprint image"]')
    await expect(uploadButton).toBeVisible()
  })

  test('suggestion chips are visible', async ({ page }) => {
    await page.goto('/estimator')

    const suggestions = page.locator('button[type="button"]').filter({ hasText: /Kitchen sink|Water heater|house repipe/ })
    await expect(suggestions.first()).toBeVisible()
  })

  test('can type a message and send button enables', async ({ page }) => {
    await page.goto('/estimator')

    const chatInput = page.locator('textarea[aria-label="Type a pricing question"]')
    const sendButton = page.locator('button[aria-label="Send message"]')

    await expect(sendButton).toBeDisabled()
    await chatInput.fill('Replace a toilet in Dallas')
    await expect(sendButton).toBeEnabled()
  })

  test('new conversation button clears messages', async ({ page }) => {
    await page.goto('/estimator')

    const chatInput = page.locator('textarea[aria-label="Type a pricing question"]')
    await chatInput.fill('Test message')
    await page.keyboard.press('Enter')

    // Wait for message to appear
    await expect(page.locator('text=Test message')).toBeVisible()

    // Click new conversation
    const newConvButton = page.locator('button:has-text("New conversation")')
    if (await newConvButton.isVisible()) {
      await newConvButton.click()
      await expect(page.locator('text=Test message')).not.toBeVisible()
    }
  })
})
