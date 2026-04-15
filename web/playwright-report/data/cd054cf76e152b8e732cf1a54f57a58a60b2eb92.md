# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: login.spec.ts >> Login Flow >> can navigate to forgot password
- Location: tests/e2e/login.spec.ts:10:7

# Error details

```
Error: page.goto: net::ERR_CONNECTION_REFUSED at http://localhost:3000/login
Call log:
  - navigating to "http://localhost:3000/login", waiting until "load"

```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | 
  3  | test.describe('Login Flow', () => {
  4  |   test('login page loads', async ({ page }) => {
  5  |     await page.goto('/login');
  6  |     await expect(page).toHaveURL(/\/login/);
  7  |     await expect(page.locator('body')).toBeVisible();
  8  |   });
  9  | 
  10 |   test('can navigate to forgot password', async ({ page }) => {
> 11 |     await page.goto('/login');
     |                ^ Error: page.goto: net::ERR_CONNECTION_REFUSED at http://localhost:3000/login
  12 |     const forgotLink = page.locator('a:has-text("Forgot")').first();
  13 |     if (await forgotLink.isVisible()) {
  14 |       await forgotLink.click();
  15 |       await expect(page).toHaveURL(/\/forgot-password/);
  16 |     }
  17 |   });
  18 | });
  19 | 
```