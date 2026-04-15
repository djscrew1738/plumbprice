import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
  test('admin page is accessible', async ({ page }) => {
    await page.goto('/admin');
    await expect(page).toHaveURL(/\/admin/);
    await expect(page.locator('body')).toBeVisible();
  });

  test('blueprints page loads', async ({ page }) => {
    await page.goto('/blueprints');
    await expect(page).toHaveURL(/\/blueprints/);
    await expect(page.locator('body')).toBeVisible();
  });

  test('pipeline page loads', async ({ page }) => {
    await page.goto('/pipeline');
    await expect(page).toHaveURL(/\/pipeline/);
    await expect(page.locator('body')).toBeVisible();
  });

  test('suppliers page loads', async ({ page }) => {
    await page.goto('/suppliers');
    await expect(page).toHaveURL(/\/suppliers/);
    await expect(page.locator('body')).toBeVisible();
  });

  test('proposals page loads', async ({ page }) => {
    await page.goto('/proposals');
    await expect(page).toHaveURL(/\/proposals/);
    await expect(page.locator('body')).toBeVisible();
  });
});
