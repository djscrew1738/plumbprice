import { test, expect } from '@playwright/test';

test.describe('Projects Page', () => {
  test('projects page loads', async ({ page }) => {
    await page.goto('/');
    // Navigate to projects or check if visible on home
    const projectsLink = page.locator('a:has-text("Projects"), a:has-text("projects")').first();
    if (await projectsLink.isVisible()) {
      await projectsLink.click();
    }
    await expect(page.locator('body')).toBeVisible();
  });

  test('estimates page loads', async ({ page }) => {
    await page.goto('/estimates');
    await expect(page).toHaveURL(/\/estimates/);
    await expect(page.locator('body')).toBeVisible();
  });

  test('estimator page loads', async ({ page }) => {
    await page.goto('/estimator');
    await expect(page).toHaveURL(/\/estimator/);
    await expect(page.locator('body')).toBeVisible();
  });
});
