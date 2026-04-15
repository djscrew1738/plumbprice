# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: projects.spec.ts >> Projects Page >> estimates page loads
- Location: tests/e2e/projects.spec.ts:14:7

# Error details

```
Error: page.goto: net::ERR_CONNECTION_REFUSED at http://localhost:3000/estimates
Call log:
  - navigating to "http://localhost:3000/estimates", waiting until "load"

```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | 
  3  | test.describe('Projects Page', () => {
  4  |   test('projects page loads', async ({ page }) => {
  5  |     await page.goto('/');
  6  |     // Navigate to projects or check if visible on home
  7  |     const projectsLink = page.locator('a:has-text("Projects"), a:has-text("projects")').first();
  8  |     if (await projectsLink.isVisible()) {
  9  |       await projectsLink.click();
  10 |     }
  11 |     await expect(page.locator('body')).toBeVisible();
  12 |   });
  13 | 
  14 |   test('estimates page loads', async ({ page }) => {
> 15 |     await page.goto('/estimates');
     |                ^ Error: page.goto: net::ERR_CONNECTION_REFUSED at http://localhost:3000/estimates
  16 |     await expect(page).toHaveURL(/\/estimates/);
  17 |     await expect(page.locator('body')).toBeVisible();
  18 |   });
  19 | 
  20 |   test('estimator page loads', async ({ page }) => {
  21 |     await page.goto('/estimator');
  22 |     await expect(page).toHaveURL(/\/estimator/);
  23 |     await expect(page.locator('body')).toBeVisible();
  24 |   });
  25 | });
  26 | 
```