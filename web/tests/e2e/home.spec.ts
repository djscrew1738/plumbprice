import { test, expect } from '@playwright/test';

test('homepage loads (smoke)', async ({ page }) => {
  await page.goto('/');
  // Basic smoke checks - ensure page loads and has a visible body element
  await expect(page).toHaveURL(/\/?$/);
  await expect(page.locator('body')).toBeVisible();
});
