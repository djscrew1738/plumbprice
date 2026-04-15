# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: navigation.spec.ts >> Navigation >> pipeline page loads
- Location: tests/e2e/navigation.spec.ts:16:7

# Error details

```
Error: page.goto: net::ERR_CONNECTION_REFUSED at http://localhost:3000/pipeline
Call log:
  - navigating to "http://localhost:3000/pipeline", waiting until "load"

```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | 
  3  | test.describe('Navigation', () => {
  4  |   test('admin page is accessible', async ({ page }) => {
  5  |     await page.goto('/admin');
  6  |     await expect(page).toHaveURL(/\/admin/);
  7  |     await expect(page.locator('body')).toBeVisible();
  8  |   });
  9  | 
  10 |   test('blueprints page loads', async ({ page }) => {
  11 |     await page.goto('/blueprints');
  12 |     await expect(page).toHaveURL(/\/blueprints/);
  13 |     await expect(page.locator('body')).toBeVisible();
  14 |   });
  15 | 
  16 |   test('pipeline page loads', async ({ page }) => {
> 17 |     await page.goto('/pipeline');
     |                ^ Error: page.goto: net::ERR_CONNECTION_REFUSED at http://localhost:3000/pipeline
  18 |     await expect(page).toHaveURL(/\/pipeline/);
  19 |     await expect(page.locator('body')).toBeVisible();
  20 |   });
  21 | 
  22 |   test('suppliers page loads', async ({ page }) => {
  23 |     await page.goto('/suppliers');
  24 |     await expect(page).toHaveURL(/\/suppliers/);
  25 |     await expect(page.locator('body')).toBeVisible();
  26 |   });
  27 | 
  28 |   test('proposals page loads', async ({ page }) => {
  29 |     await page.goto('/proposals');
  30 |     await expect(page).toHaveURL(/\/proposals/);
  31 |     await expect(page.locator('body')).toBeVisible();
  32 |   });
  33 | });
  34 | 
```