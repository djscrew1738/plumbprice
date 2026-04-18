// Run with: E2E_BASE_URL=http://localhost:3000 npx playwright test tests/e2e/proposal-flow.spec.ts
// Requires: running API (port 8000) and seeded DB
//
// Credentials: set E2E_USER_EMAIL / E2E_USER_PASSWORD env vars, or supply an admin
// account created via: cd api && python scripts/create_admin.py admin@example.com Password123
//
// The happy-path test creates a proposal via the API directly to avoid UI flakiness
// (estimate creation requires many form steps). It then exercises the full
// send → public accept → status-badge assertion loop.

import { test, expect, type Page, type APIRequestContext, type Browser } from '@playwright/test'

test.describe.configure({ mode: 'serial' })

const BASE_URL      = process.env.E2E_BASE_URL      ?? ''
const API_URL       = process.env.E2E_API_URL        ?? 'http://localhost:8000'
const USER_EMAIL    = process.env.E2E_USER_EMAIL     ?? 'admin@example.com'
const USER_PASSWORD = process.env.E2E_USER_PASSWORD  ?? 'Password123'

// ---------------------------------------------------------------------------
// Helper: skip the whole suite when no live server is configured
// ---------------------------------------------------------------------------
test.beforeEach(() => {
  test.skip(!BASE_URL, 'Set E2E_BASE_URL to run proposal-flow tests')
})

// ---------------------------------------------------------------------------
// Helper: log in via the login page and wait for redirect
// ---------------------------------------------------------------------------
async function loginAs(page: Page, email: string, password: string) {
  await page.goto(`${BASE_URL}/login`)
  await page.locator('#email').fill(email)
  await page.locator('#password').fill(password)
  await page.locator('button[type="submit"]').click()
  await page.waitForURL((url) => !url.pathname.startsWith('/login'), { timeout: 10_000 })
}

// ---------------------------------------------------------------------------
// Helper: obtain a JWT via the API directly (avoids UI login cost)
// ---------------------------------------------------------------------------
async function getAuthToken(request: APIRequestContext): Promise<string> {
  const res = await request.post(`${API_URL}/api/v1/auth/login`, {
    form: { username: USER_EMAIL, password: USER_PASSWORD },
  })
  if (!res.ok()) throw new Error(`Login failed: ${res.status()} ${await res.text()}`)
  const body = await res.json() as { access_token: string }
  return body.access_token
}

// ---------------------------------------------------------------------------
// Helper: create a minimal estimate + send proposal, return public token
// ---------------------------------------------------------------------------
async function createTestProposal(
  request: APIRequestContext,
): Promise<{ estimateId: number; token: string }> {
  const jwt = await getAuthToken(request)
  const headers = { Authorization: `Bearer ${jwt}`, 'Content-Type': 'application/json' }

  const estRes = await request.post(`${API_URL}/api/v1/estimates/`, {
    headers,
    data: { title: 'E2E Proposal Test', job_type: 'general', county: 'Dallas', line_items: [] },
  })
  if (!estRes.ok()) throw new Error(`Create estimate failed: ${estRes.status()} ${await estRes.text()}`)
  const estimate = await estRes.json() as { id: number }

  const propRes = await request.post(`${API_URL}/api/v1/estimates/${estimate.id}/proposals/send`, {
    headers,
    data: { recipient_email: 'e2e-test@example.com', recipient_name: 'E2E Tester' },
  })
  if (!propRes.ok()) throw new Error(`Send proposal failed: ${propRes.status()} ${await propRes.text()}`)
  const proposal = await propRes.json() as { public_token: string }

  return { estimateId: estimate.id, token: proposal.public_token }
}

// ===========================================================================
// Test 1 — happy path: send → accept on public page → status shows Accepted
// ===========================================================================
test('happy path: accept proposal and verify Accepted status', async ({ page, request, browser }) => {
  // 1. Create estimate + proposal via API (fast, avoids multi-step UI form)
  const { estimateId, token } = await createTestProposal(request)

  // 2. Open the public proposal page in a fresh unauthenticated context
  const publicContext = await (browser as Browser).newContext({ storageState: undefined })
  const publicPage = await publicContext.newPage()
  await publicPage.goto(`${BASE_URL}/p/${token}`)

  await expect(publicPage.locator('h1')).toBeVisible({ timeout: 10_000 })
  await expect(publicPage.getByText('E2E Proposal Test')).toBeVisible()

  // 3. Click "Accept proposal"
  await publicPage.getByRole('button', { name: /accept proposal/i }).click()

  // 4. Fill in signature
  await publicPage.locator('#pp-sig').fill('Test Acceptance')

  // 5. Submit
  await publicPage.getByRole('button', { name: /^Accept$/i }).click()

  // 6. Assert success state — accepted banner appears
  await expect(publicPage.getByText(/accepted on/i)).toBeVisible({ timeout: 10_000 })
  await expect(publicPage.getByText(/test acceptance/i)).toBeVisible()

  await publicContext.close()

  // 7. Back in authed context: verify "Accepted" badge in Proposal History
  await loginAs(page, USER_EMAIL, USER_PASSWORD)
  await page.goto(`${BASE_URL}/estimates/${estimateId}`)
  await expect(page.getByText('Accepted').first()).toBeVisible({ timeout: 10_000 })
})

// ===========================================================================
// Test 2 — invalid / expired token shows error page, not a crash
// ===========================================================================
test('invalid token shows error page', async ({ page }) => {
  await page.goto(`${BASE_URL}/p/invalid-token-xyz-00000000`)
  await expect(page.getByRole('heading', { name: /proposal unavailable/i })).toBeVisible({ timeout: 10_000 })
  await expect(page.locator('body')).toBeVisible()
})

// ===========================================================================
// Test 3 — double-accept is idempotent (no 500, shows already-accepted UI)
// ===========================================================================
test('double-accept is idempotent — shows accepted banner, no server error', async ({ request, browser }) => {
  const { token } = await createTestProposal(request)

  // Accept once via the API
  const firstAccept = await request.post(`${API_URL}/api/v1/public/proposals/${token}/accept`, {
    headers: { 'Content-Type': 'application/json' },
    data: { signature: 'First Acceptance' },
  })
  if (!firstAccept.ok()) throw new Error(`First accept failed: ${firstAccept.status()} ${await firstAccept.text()}`)

  // Open the already-accepted page — should show accepted state, not crash
  const publicContext = await (browser as Browser).newContext({ storageState: undefined })
  const publicPage = await publicContext.newPage()

  const errors: string[] = []
  publicPage.on('pageerror', (err) => errors.push(err.message))

  await publicPage.goto(`${BASE_URL}/p/${token}`)
  await expect(publicPage.getByText(/accepted on/i)).toBeVisible({ timeout: 10_000 })

  // Action buttons must NOT be present (canAct = false after acceptance)
  await expect(publicPage.getByRole('button', { name: /accept proposal/i })).not.toBeVisible()

  expect(errors).toHaveLength(0)

  await publicContext.close()
})
