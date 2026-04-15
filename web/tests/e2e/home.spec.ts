import { test, expect } from '@playwright/test';

test('homepage loads and shows Projects link', async ({ page }) => {
  await page.goto('/');
  // Basic smoke checks - adjust selectors if the app layout changes
  await expect(page).toHaveURL(/\/?$/);
  await expect(page.locator('text=Projects').first()).toBeVisible();
});
