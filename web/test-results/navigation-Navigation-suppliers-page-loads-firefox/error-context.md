# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: navigation.spec.ts >> Navigation >> suppliers page loads
- Location: tests/e2e/navigation.spec.ts:22:7

# Error details

```
Error: page.goto: NS_ERROR_CONNECTION_REFUSED
Call log:
  - navigating to "http://localhost:3000/suppliers", waiting until "load"

```

# Page snapshot

```yaml
- generic [ref=e2]:
  - generic [ref=e3]:
    - heading "Unable to connect" [level=1] [ref=e5]
    - paragraph [ref=e6]: Firefox can’t establish a connection to the server at localhost:3000.
    - paragraph
    - list [ref=e8]:
      - listitem [ref=e9]: The site could be temporarily unavailable or too busy. Try again in a few moments.
      - listitem [ref=e10]: If you are unable to load any pages, check your computer’s network connection.
      - listitem [ref=e11]: If your computer or network is protected by a firewall or proxy, make sure that Nightly is permitted to access the web.
  - button "Try Again" [active] [ref=e13]
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
  17 |     await page.goto('/pipeline');
  18 |     await expect(page).toHaveURL(/\/pipeline/);
  19 |     await expect(page.locator('body')).toBeVisible();
  20 |   });
  21 | 
  22 |   test('suppliers page loads', async ({ page }) => {
> 23 |     await page.goto('/suppliers');
     |                ^ Error: page.goto: NS_ERROR_CONNECTION_REFUSED
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