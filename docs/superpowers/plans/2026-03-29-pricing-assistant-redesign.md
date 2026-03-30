# Pricing Assistant Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the current dark estimator dashboard into a unified pricing assistant workspace for repair, blueprint, and floorplan estimating, then harden the supporting pages so the frontend is ready for production release.

**Architecture:** Keep the existing Next.js routes and backend contracts, but replace the frontend shell and estimator experience with a new workspace composition. Introduce a small set of focused workspace components instead of expanding `EstimatorPage.tsx`, and wire the summary rail from the existing chat estimate payload so the redesign is largely frontend-only.

**Tech Stack:** Next.js App Router, React 19, TypeScript, Tailwind CSS, Framer Motion, Axios, ESLint, production `next build`

---

## File Structure

### Existing files to modify

- `web/package.json`
- `web/src/app/globals.css`
- `web/src/app/layout.tsx`
- `web/src/app/page.tsx`
- `web/src/app/estimator/page.tsx`
- `web/src/components/layout/Header.tsx`
- `web/src/components/layout/Sidebar.tsx`
- `web/src/components/layout/MobileNav.tsx`
- `web/src/components/estimator/EstimatorPage.tsx`
- `web/src/components/estimator/EstimateBreakdown.tsx`
- `web/src/components/estimator/ConfidenceBadge.tsx`
- `web/src/components/estimates/EstimatesListPage.tsx`
- `web/src/components/pipeline/PipelinePage.tsx`
- `web/src/components/suppliers/SuppliersPage.tsx`
- `web/src/components/admin/AdminPage.tsx`

### New files to create

- `web/vitest.config.ts`
- `web/src/test/setup.ts`
- `web/src/components/workspace/WorkspaceModeSwitcher.tsx`
- `web/src/components/workspace/WorkspacePromptComposer.tsx`
- `web/src/components/workspace/WorkspaceSummaryRail.tsx`
- `web/src/components/workspace/WorkspaceEmptyState.tsx`
- `web/src/components/workspace/WorkspaceArtifactCard.tsx`
- `web/src/components/workspace/RecentJobsRail.tsx`
- `web/src/components/workspace/WorkspaceModeSwitcher.test.tsx`
- `web/src/components/workspace/WorkspaceSummaryRail.test.tsx`

The new `workspace` directory keeps the redesigned assistant UI decomposed into focused units instead of making `EstimatorPage.tsx` even larger.

### Existing files used for verification

- `web/src/lib/api.ts`
- `web/src/lib/utils.ts`
- `web/src/types/index.ts`

## Task 1: Add frontend test infrastructure for the redesigned workspace

**Files:**
- Modify: `web/package.json`
- Create: `web/vitest.config.ts`
- Create: `web/src/test/setup.ts`
- Test: `web/src/components/workspace/WorkspaceModeSwitcher.test.tsx`

- [ ] **Step 1: Write the failing test for workspace mode switching**

```tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { WorkspaceModeSwitcher } from './WorkspaceModeSwitcher'

describe('WorkspaceModeSwitcher', () => {
  it('renders all estimating modes and notifies when the user switches modes', async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()

    render(<WorkspaceModeSwitcher mode="repair" onChange={onChange} />)

    expect(screen.getByRole('button', { name: /repair pricing/i })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: /blueprint pricing/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /floorplan pricing/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /blueprint pricing/i }))

    expect(onChange).toHaveBeenCalledWith('blueprint')
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd web && npx vitest run src/components/workspace/WorkspaceModeSwitcher.test.tsx`
Expected: FAIL because `WorkspaceModeSwitcher` and the Vitest config do not exist yet.

- [ ] **Step 3: Add the minimal test tooling**

```json
{
  "scripts": {
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.6.3",
    "@testing-library/react": "^16.2.0",
    "@testing-library/user-event": "^14.6.1",
    "jsdom": "^25.0.1",
    "vitest": "^2.1.8"
  }
}
```

```ts
// web/vitest.config.ts
import { defineConfig } from 'vitest/config'
import path from 'node:path'

export default defineConfig({
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
```

```ts
// web/src/test/setup.ts
import '@testing-library/jest-dom'
```

- [ ] **Step 4: Add the minimal component implementation to make the test pass**

```tsx
// web/src/components/workspace/WorkspaceModeSwitcher.tsx
'use client'

const MODES = [
  { value: 'repair', label: 'Repair Pricing', blurb: 'Fast service pricing for field work.' },
  { value: 'blueprint', label: 'Blueprint Pricing', blurb: 'Upload plans and review takeoff assumptions.' },
  { value: 'floorplan', label: 'Floorplan Pricing', blurb: 'Guide rough-in and finish estimates from plan context.' },
] as const

export type WorkspaceMode = (typeof MODES)[number]['value']

export function WorkspaceModeSwitcher({
  mode,
  onChange,
}: {
  mode: WorkspaceMode
  onChange: (mode: WorkspaceMode) => void
}) {
  return (
    <div className="grid gap-3 md:grid-cols-3">
      {MODES.map(option => (
        <button
          key={option.value}
          type="button"
          aria-pressed={mode === option.value}
          onClick={() => onChange(option.value)}
          className="rounded-[1.5rem] border p-4 text-left"
        >
          <span className="block text-sm font-semibold">{option.label}</span>
          <span className="mt-1 block text-sm text-slate-500">{option.blurb}</span>
        </button>
      ))}
    </div>
  )
}
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd web && npx vitest run src/components/workspace/WorkspaceModeSwitcher.test.tsx`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add web/package.json web/package-lock.json web/vitest.config.ts web/src/test/setup.ts web/src/components/workspace/WorkspaceModeSwitcher.tsx web/src/components/workspace/WorkspaceModeSwitcher.test.tsx
git commit -m "test: add workspace frontend test harness"
```

## Task 2: Replace the global theme and shell with the new workspace framing

**Files:**
- Modify: `web/src/app/globals.css`
- Modify: `web/src/app/layout.tsx`
- Modify: `web/src/components/layout/Header.tsx`
- Modify: `web/src/components/layout/Sidebar.tsx`
- Modify: `web/src/components/layout/MobileNav.tsx`
- Test: `web/src/app/layout.tsx` via lint and build

- [ ] **Step 1: Write the failing verification for the new shell**

Add a lightweight smoke assertion inside the workspace shell test file to lock the new labels:

```tsx
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Header } from '@/components/layout/Header'

describe('Header', () => {
  it('shows the workspace-oriented title copy', () => {
    render(<Header onMenuClick={() => {}} />)
    expect(screen.getByText(/pricing workspace/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd web && npx vitest run src/components/layout/Header.test.tsx`
Expected: FAIL because the current header still renders the old estimator title and there is no test file yet.

- [ ] **Step 3: Implement the minimal shell redesign**

```tsx
// web/src/app/layout.tsx
<html lang="en">
  <body className="min-h-dvh bg-[var(--canvas)] text-[var(--ink)]">
    <ToastProvider>
      <div className="relative flex min-h-dvh bg-[radial-gradient(circle_at_top_left,_rgba(196,116,55,0.12),_transparent_32%),linear-gradient(180deg,#f7f3ec_0%,#f2ede3_100%)]">
        <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
        <div className="flex min-h-dvh flex-1 flex-col lg:ml-[272px]">
          <Header onMenuClick={() => setSidebarOpen(true)} />
          <main className="flex-1 overflow-x-hidden overflow-y-auto">{children}</main>
        </div>
        <MobileNav />
      </div>
    </ToastProvider>
  </body>
</html>
```

```css
/* web/src/app/globals.css */
:root {
  --canvas: #f2ede3;
  --panel: rgba(255, 252, 247, 0.88);
  --panel-strong: #fffdf8;
  --ink: #1f2933;
  --muted-ink: #667085;
  --line: rgba(31, 41, 51, 0.08);
  --accent: #b8622e;
  --accent-strong: #8e4a23;
  --accent-soft: rgba(184, 98, 46, 0.12);
  --shadow-lg: 0 30px 60px rgba(39, 33, 24, 0.12);
}
```

```tsx
// web/src/components/layout/Header.tsx
const pages = {
  '/': { title: 'Pricing Workspace', eyebrow: 'Unified estimating assistant' },
  '/estimator': { title: 'Pricing Workspace', eyebrow: 'Unified estimating assistant' },
  '/estimates': { title: 'Saved Estimates', eyebrow: 'Review and continue active bids' },
  '/pipeline': { title: 'Pipeline', eyebrow: 'Commercial follow-through and status' },
  '/suppliers': { title: 'Suppliers', eyebrow: 'Pricing sources and coverage' },
  '/admin': { title: 'Admin', eyebrow: 'System controls' },
}
```

```tsx
// web/src/components/layout/Sidebar.tsx
const CORE_NAV = [
  { href: '/estimator', label: 'Workspace' },
  { href: '/estimates', label: 'Saved Estimates' },
  { href: '/pipeline', label: 'Pipeline' },
]
```

- [ ] **Step 4: Run verification for the shell**

Run: `cd web && npm run lint`
Expected: PASS with no ESLint warnings

Run: `cd web && npm run build`
Expected: PASS with a successful Next.js production build

- [ ] **Step 5: Commit**

```bash
git add web/src/app/globals.css web/src/app/layout.tsx web/src/components/layout/Header.tsx web/src/components/layout/Sidebar.tsx web/src/components/layout/MobileNav.tsx web/src/components/layout/Header.test.tsx
git commit -m "feat: redesign app shell for pricing workspace"
```

## Task 3: Rebuild the estimator route as the unified pricing workspace

**Files:**
- Modify: `web/src/app/page.tsx`
- Modify: `web/src/app/estimator/page.tsx`
- Modify: `web/src/components/estimator/EstimatorPage.tsx`
- Modify: `web/src/components/estimator/EstimateBreakdown.tsx`
- Modify: `web/src/components/estimator/ConfidenceBadge.tsx`
- Create: `web/src/components/workspace/WorkspacePromptComposer.tsx`
- Create: `web/src/components/workspace/WorkspaceSummaryRail.tsx`
- Create: `web/src/components/workspace/WorkspaceEmptyState.tsx`
- Create: `web/src/components/workspace/WorkspaceArtifactCard.tsx`
- Create: `web/src/components/workspace/RecentJobsRail.tsx`
- Test: `web/src/components/workspace/WorkspaceSummaryRail.test.tsx`

- [ ] **Step 1: Write the failing test for the summary rail**

```tsx
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { WorkspaceSummaryRail } from './WorkspaceSummaryRail'

describe('WorkspaceSummaryRail', () => {
  it('renders totals, confidence, and assumptions for the active estimate', () => {
    render(
      <WorkspaceSummaryRail
        estimate={{
          total: '$1,240',
          range: '$1,110 - $1,380',
          confidenceLabel: 'High confidence',
          assumptions: ['Assumes standard access', 'Includes disposal haul-away'],
        }}
      />
    )

    expect(screen.getByText('$1,240')).toBeInTheDocument()
    expect(screen.getByText(/high confidence/i)).toBeInTheDocument()
    expect(screen.getByText(/assumes standard access/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd web && npx vitest run src/components/workspace/WorkspaceSummaryRail.test.tsx`
Expected: FAIL because `WorkspaceSummaryRail` does not exist yet.

- [ ] **Step 3: Implement the workspace components and estimator composition**

```tsx
// web/src/components/workspace/WorkspaceSummaryRail.tsx
export function WorkspaceSummaryRail({
  estimate,
}: {
  estimate: {
    total: string
    range: string
    confidenceLabel: string
    assumptions: string[]
  } | null
}) {
  if (!estimate) {
    return (
      <aside className="rounded-[2rem] border border-[var(--line)] bg-[var(--panel)] p-6 shadow-[var(--shadow-lg)]">
        <p className="text-sm font-medium text-[var(--muted-ink)]">Run a price request to see totals, confidence, and extracted scope.</p>
      </aside>
    )
  }

  return (
    <aside className="rounded-[2rem] border border-[var(--line)] bg-[var(--panel-strong)] p-6 shadow-[var(--shadow-lg)]">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--muted-ink)]">Active estimate</p>
      <h2 className="mt-3 text-4xl font-semibold text-[var(--ink)]">{estimate.total}</h2>
      <p className="mt-1 text-sm text-[var(--muted-ink)]">{estimate.range}</p>
      <div className="mt-6 rounded-[1.5rem] bg-[var(--accent-soft)] p-4 text-sm font-medium text-[var(--accent-strong)]">
        {estimate.confidenceLabel}
      </div>
      <ul className="mt-6 space-y-3 text-sm text-[var(--ink)]">
        {estimate.assumptions.map(item => <li key={item}>{item}</li>)}
      </ul>
    </aside>
  )
}
```

```tsx
// web/src/components/estimator/EstimatorPage.tsx
const [mode, setMode] = useState<WorkspaceMode>('repair')

return (
  <div className="mx-auto flex w-full max-w-[1600px] gap-6 px-4 py-5 lg:px-6">
    <RecentJobsRail />
    <section className="min-w-0 flex-1">
      <WorkspaceModeSwitcher mode={mode} onChange={setMode} />
      <WorkspacePromptComposer
        mode={mode}
        county={county}
        input={input}
        loading={loading}
        onCountyChange={setCounty}
        onInputChange={setInput}
        onSubmit={sendMessage}
      />
      {messages.length === 0 ? (
        <WorkspaceEmptyState mode={mode} onSuggestionClick={sendMessage} />
      ) : (
        <div className="space-y-4">
          {messages.map(msg => <WorkspaceArtifactCard key={msg.id} message={msg} onCopy={copyMessage} />)}
        </div>
      )}
    </section>
    <div className="hidden w-[360px] xl:block">
      <WorkspaceSummaryRail estimate={activeEstimateSummary} />
    </div>
  </div>
)
```

```tsx
// web/src/app/page.tsx
export default function Home() {
  return <EstimatorPage />
}
```

- [ ] **Step 4: Run targeted tests and app verification**

Run: `cd web && npx vitest run src/components/workspace/WorkspaceModeSwitcher.test.tsx src/components/workspace/WorkspaceSummaryRail.test.tsx`
Expected: PASS

Run: `cd web && npm run lint`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/src/app/page.tsx web/src/app/estimator/page.tsx web/src/components/estimator/EstimatorPage.tsx web/src/components/estimator/EstimateBreakdown.tsx web/src/components/estimator/ConfidenceBadge.tsx web/src/components/workspace
git commit -m "feat: rebuild estimator as unified pricing workspace"
```

## Task 4: Turn the estimates page into a work queue aligned with the new system

**Files:**
- Modify: `web/src/components/estimates/EstimatesListPage.tsx`
- Test: `web/src/components/estimates/EstimatesListPage.tsx` via lint and build

- [ ] **Step 1: Write the failing test for the revised page headings**

```tsx
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { EstimatesListPage } from './EstimatesListPage'

vi.mock('@/lib/api', () => ({
  api: {
    get: vi.fn().mockResolvedValue({ data: { estimates: [] } }),
    delete: vi.fn(),
  },
}))

describe('EstimatesListPage', () => {
  it('shows the work-queue framing copy', async () => {
    render(<EstimatesListPage />)
    expect(await screen.findByText(/saved estimates/i)).toBeInTheDocument()
    expect(screen.getByText(/continue active bids/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd web && npx vitest run src/components/estimates/EstimatesListPage.test.tsx`
Expected: FAIL because the file and new copy do not exist yet.

- [ ] **Step 3: Implement the work-queue redesign**

```tsx
// web/src/components/estimates/EstimatesListPage.tsx
<div className="mx-auto max-w-6xl px-4 py-6 lg:px-6">
  <section className="rounded-[2rem] border border-[var(--line)] bg-[var(--panel)] p-6 shadow-[var(--shadow-lg)]">
    <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--muted-ink)]">Saved estimates</p>
    <div className="mt-3 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <h1 className="text-3xl font-semibold text-[var(--ink)]">Continue active bids</h1>
        <p className="mt-2 max-w-2xl text-sm text-[var(--muted-ink)]">Review recent pricing work, scan confidence, and reopen estimates without digging through utility screens.</p>
      </div>
    </div>
  </section>
</div>
```

Use larger summary cards, cleaner filters, and rows/cards that clearly show:

- title
- estimate type
- county
- confidence label
- created date
- grand total

- [ ] **Step 4: Run verification**

Run: `cd web && npx vitest run src/components/estimates/EstimatesListPage.test.tsx`
Expected: PASS

Run: `cd web && npm run lint && npm run build`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/src/components/estimates/EstimatesListPage.tsx web/src/components/estimates/EstimatesListPage.test.tsx
git commit -m "feat: redesign saved estimates work queue"
```

## Task 5: Restyle pipeline, suppliers, and admin into secondary utility pages

**Files:**
- Modify: `web/src/components/pipeline/PipelinePage.tsx`
- Modify: `web/src/components/suppliers/SuppliersPage.tsx`
- Modify: `web/src/components/admin/AdminPage.tsx`
- Test: production lint/build and manual browser verification

- [ ] **Step 1: Write the failing assertions for secondary page framing**

```tsx
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { PipelinePage } from './PipelinePage'

describe('PipelinePage', () => {
  it('uses the new supporting-workflow heading copy', () => {
    render(<PipelinePage />)
    expect(screen.getByText(/pipeline/i)).toBeInTheDocument()
    expect(screen.getByText(/commercial follow-through/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd web && npx vitest run src/components/pipeline/PipelinePage.test.tsx`
Expected: FAIL because the test file and updated heading copy do not exist yet.

- [ ] **Step 3: Implement the secondary-page consistency pass**

Apply the same shell conventions to all three pages:

```tsx
<section className="rounded-[2rem] border border-[var(--line)] bg-[var(--panel)] p-6 shadow-[var(--shadow-lg)]">
  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--muted-ink)]">Pipeline</p>
  <h1 className="mt-3 text-3xl font-semibold text-[var(--ink)]">Commercial follow-through</h1>
  <p className="mt-2 text-sm text-[var(--muted-ink)]">Track estimate status and keep sales activity visually subordinate to the pricing workspace.</p>
</section>
```

Do the equivalent for suppliers and admin so controls, spacing, tables, and empty states share the new palette and typography.

- [ ] **Step 4: Run full verification**

Run: `cd web && npm run test`
Expected: PASS

Run: `cd web && npm run lint`
Expected: PASS

Run: `cd web && npm run build`
Expected: PASS

Run: `cd web && npm run dev`
Expected: App boots locally for manual desktop and mobile checks

Manual checks:

- Open `/estimator`, `/estimates`, `/pipeline`, `/suppliers`, and `/admin`
- Verify desktop layout at roughly `1440px` width
- Verify mobile layout at roughly `390px` width
- Confirm the workspace summary rail stacks correctly on mobile
- Confirm there are no unreadable low-contrast states

- [ ] **Step 5: Commit**

```bash
git add web/src/components/pipeline/PipelinePage.tsx web/src/components/suppliers/SuppliersPage.tsx web/src/components/admin/AdminPage.tsx
git commit -m "feat: align secondary pages with workspace redesign"
```

## Task 6: Production release verification and deployment preparation

**Files:**
- Review: `docs/DEPLOYMENT.md`
- Review: Docker and runtime config already in repo
- Test: final production build and deployment checklist

- [ ] **Step 1: Verify the final production artifact**

Run: `cd web && npm run build`
Expected: PASS with no missing imports, type failures, or route-generation errors

- [ ] **Step 2: Verify the repo-level deployment path**

Run: `sed -n '1,220p' docs/DEPLOYMENT.md`
Expected: Confirms the current Docker-based release path and any required env vars for `app.ctlplumbingllc.com`

- [ ] **Step 3: Prepare the release summary**

Document:

- routes changed
- new test commands
- required env assumptions
- any blueprint/floorplan capabilities that are UI-ready but backend-partial

- [ ] **Step 4: Commit the final integrated redesign**

```bash
git add web docs/superpowers/plans/2026-03-29-pricing-assistant-redesign.md
git commit -m "feat: ship pricing assistant workspace redesign"
```

## Self-Review

### Spec coverage

- Unified workspace: covered by Task 3
- Light editorial visual system and shell: covered by Task 2
- Saved estimates queue refresh: covered by Task 4
- Secondary utility pages: covered by Task 5
- Production readiness checks: covered by Task 6

### Placeholder scan

The plan includes exact file paths, explicit commands, and concrete starter code. The remaining broad language in Task 5 is limited to style application across existing pages; the page shell snippet and verification expectations define the intended implementation shape.

### Type consistency

- `WorkspaceMode` values are consistent across mode-switching and workspace composition steps
- The summary rail interface uses `total`, `range`, `confidenceLabel`, and `assumptions` consistently
- The shell copy updates match the approved spec language around `Pricing Workspace`, `Saved Estimates`, and `Pipeline`
