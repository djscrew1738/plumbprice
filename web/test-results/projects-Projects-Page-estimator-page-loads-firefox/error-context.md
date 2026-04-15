# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: projects.spec.ts >> Projects Page >> estimator page loads
- Location: tests/e2e/projects.spec.ts:20:7

# Error details

```
Error: page.goto: NS_ERROR_CONNECTION_REFUSED
Call log:
  - navigating to "http://localhost:3000/estimator", waiting until "load"

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
  15 |     await page.goto('/estimates');
  16 |     await expect(page).toHaveURL(/\/estimates/);
  17 |     await expect(page.locator('body')).toBeVisible();
  18 |   });
  19 | 
  20 |   test('estimator page loads', async ({ page }) => {
> 21 |     await page.goto('/estimator');
     |                ^ Error: page.goto: NS_ERROR_CONNECTION_REFUSED
  22 |     await expect(page).toHaveURL(/\/estimator/);
  23 |     await expect(page.locator('body')).toBeVisible();
  24 |   });
  25 | });
  26 | 
```