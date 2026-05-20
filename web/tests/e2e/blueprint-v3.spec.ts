import { test, expect } from '@playwright/test'

test.describe('Blueprint v3', () => {
  test('blueprints page loads', async ({ page }) => {
    await page.goto('/blueprints')
    await expect(page).toHaveURL(/\/blueprints/)
    await expect(page.locator('body')).toBeVisible()
  })

  test('upload drop zone is visible', async ({ page }) => {
    await page.goto('/blueprints')

    const dropZone = page.locator('[role="button"][aria-label*="Upload blueprint"]')
    await expect(dropZone).toBeVisible()
  })

  test('estimator chat has blueprint image upload button', async ({ page }) => {
    await page.goto('/estimator')

    const uploadButton = page.locator('button[aria-label="Attach blueprint image"]')
    await expect(uploadButton).toBeVisible()

    // Clicking should open file picker (can't test actual upload without file)
    await uploadButton.click()
    const fileInput = page.locator('input[type="file"]')
    await expect(fileInput).toHaveCount(1)
  })
})
