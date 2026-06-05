import { chromium, FullConfig } from '@playwright/test'
import fs from 'fs'
import path from 'path'

async function globalSetup(_config: FullConfig) {
  const authFile = path.join(__dirname, '.auth/user.json')

  // Ensure auth dir exists
  fs.mkdirSync(path.dirname(authFile), { recursive: true })

  const browser = await chromium.launch()
  const context = await browser.newContext()
  const page = await context.newPage()

  // Log in via the API directly and set the cookie
  const response = await page.request.post('http://127.0.0.1:8200/api/v1/auth/login', {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    data: 'username=admin%40ctlplumbingllc.com&password=TestPass123!',
  })

  if (!response.ok()) {
    throw new Error(`Login failed: ${response.status()} ${await response.text()}`)
  }

  const { access_token } = await response.json() as { access_token: string }

  // Set auth cookie for the test base URL
  await context.addCookies([{
    name: 'pp_token',
    value: access_token,
    domain: 'localhost',
    path: '/',
    httpOnly: true,
    sameSite: 'Lax',
  }])

  await context.storageState({ path: authFile })
  await browser.close()
}

export default globalSetup
