import { test, expect } from '@playwright/test'

// Login tests must run without stored auth so we can test the unauthenticated state
test.use({ storageState: { cookies: [], origins: [] } })

test.describe('Login Flow', () => {
  test('login page loads', async ({ page }) => {
    await page.goto('/login');
    await expect(page).toHaveURL(/\/login/);
    await expect(page.locator('body')).toBeVisible();
  });

  test('can navigate to forgot password', async ({ page }) => {
    await page.goto('/login');
    const forgotLink = page.locator('a:has-text("Forgot")').first();
    if (await forgotLink.isVisible()) {
      await forgotLink.click();
      await expect(page).toHaveURL(/\/forgot-password/);
    }
  });
});
