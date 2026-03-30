# App Shell Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current dark dashboard shell with a mobile-first launcher home and unified pricing workspace, then roll the new shell system through the existing support pages.

**Architecture:** Keep the existing Next.js routes and backend APIs, but introduce shared shell/navigation primitives, a launcher-based home route, and a lighter workspace composition for `/estimator`. Recent jobs should be derived from the existing estimates endpoint, and the support pages should adopt the same shell language rather than staying on the old black dashboard treatment.

**Tech Stack:** Next.js App Router, React 19, TypeScript, Tailwind CSS, Framer Motion, Axios, date-fns, Vitest, ESLint, production `next build`

---

## File Structure

### Existing files to modify

- `web/src/app/globals.css`
- `web/src/app/layout.tsx`
- `web/src/app/page.tsx`
- `web/src/app/blueprints/page.tsx`
- `web/src/app/proposals/page.tsx`
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

- `web/src/components/layout/nav.ts`
- `web/src/components/layout/MoreSheet.tsx`
- `web/src/components/layout/PageIntro.tsx`
- `web/src/components/layout/MobileNav.test.tsx`
- `web/src/components/layout/MoreSheet.test.tsx`
- `web/src/components/workspace/PrimaryActionCard.tsx`
- `web/src/components/workspace/RecentJobsList.tsx`
- `web/src/components/workspace/LauncherHome.tsx`
- `web/src/components/workspace/LauncherHome.test.tsx`
- `web/src/components/workspace/WorkspaceEntryBar.tsx`
- `web/src/components/workspace/WorkspaceSummaryRail.tsx`
- `web/src/components/workspace/WorkspaceSummaryRail.test.tsx`
- `web/src/components/estimates/EstimatesListPage.test.tsx`

### File responsibilities

- `web/src/components/layout/nav.ts`: Single source of truth for primary nav, secondary links, mobile tabs, and route metadata.
- `web/src/components/layout/MoreSheet.tsx`: Mobile secondary destinations sheet for `Suppliers`, `Admin`, `Blueprints`, and `Proposals`.
- `web/src/components/layout/PageIntro.tsx`: Shared support-page heading surface so secondary pages inherit the new shell language consistently.
- `web/src/components/workspace/LauncherHome.tsx`: Mobile-first home route with the two primary action cards and a recent jobs list.
- `web/src/components/workspace/WorkspaceEntryBar.tsx`: Top-of-workspace action area for quick quote vs upload entry and county context.
- `web/src/components/workspace/WorkspaceSummaryRail.tsx`: Desktop rail and mobile summary trigger around the current estimate breakdown.

### Existing files used for verification

- `web/src/lib/api.ts`
- `web/src/lib/utils.ts`
- `web/src/types/index.ts`
- `web/package.json`
- `web/vitest.config.ts`
- `web/src/test/setup.ts`

## Task 1: Lock the field-first navigation model in tests and shared metadata

**Files:**
- Create: `web/src/components/layout/nav.ts`
- Create: `web/src/components/layout/MobileNav.test.tsx`
- Modify: `web/src/components/layout/MobileNav.tsx`
- Modify: `web/src/components/layout/Header.tsx`
- Modify: `web/src/components/layout/Sidebar.tsx`
- Test: `web/src/components/layout/MobileNav.test.tsx`

- [ ] **Step 1: Write the failing mobile navigation test**

```tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { MobileNav } from './MobileNav'

vi.mock('next/navigation', () => ({
  usePathname: () => '/',
}))

vi.mock('next/link', () => ({
  default: ({ children, href, ...props }: any) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}))

describe('MobileNav', () => {
  it('shows the field-first tabs and opens More for utility destinations', async () => {
    const onOpenMore = vi.fn()
    const user = userEvent.setup()

    render(<MobileNav onOpenMore={onOpenMore} />)

    expect(screen.getByRole('link', { name: /home/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /jobs/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /pipeline/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /more/i })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /suppliers/i })).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /more/i }))

    expect(onOpenMore).toHaveBeenCalledTimes(1)
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd web && npx vitest run src/components/layout/MobileNav.test.tsx`
Expected: FAIL because `MobileNav` does not accept `onOpenMore`, still renders `Suppliers` and `Admin` directly, and there is no shared shell navigation model yet.

- [ ] **Step 3: Implement the shared navigation metadata and mobile tab behavior**

```ts
// web/src/components/layout/nav.ts
import {
  BriefcaseBusiness,
  FileOutput,
  FileText,
  House,
  Layers,
  MessageSquareMore,
  Package,
  Settings,
  type LucideIcon,
} from 'lucide-react'

export interface AppNavItem {
  href: string
  label: string
  icon: LucideIcon
}

export const PRIMARY_NAV: AppNavItem[] = [
  { href: '/', label: 'Home', icon: House },
  { href: '/estimates', label: 'Jobs', icon: FileText },
  { href: '/pipeline', label: 'Pipeline', icon: BriefcaseBusiness },
]

export const SECONDARY_NAV: AppNavItem[] = [
  { href: '/suppliers', label: 'Suppliers', icon: Package },
  { href: '/admin', label: 'Admin', icon: Settings },
]

export const MORE_LINKS: AppNavItem[] = [
  ...SECONDARY_NAV,
  { href: '/blueprints', label: 'Blueprints', icon: Layers },
  { href: '/proposals', label: 'Proposals', icon: FileOutput },
]

export const MOBILE_TABS = [
  PRIMARY_NAV[0],
  PRIMARY_NAV[1],
  PRIMARY_NAV[2],
  { href: '#more', label: 'More', icon: MessageSquareMore },
] as const

export const PAGE_META: Record<string, { title: string; eyebrow: string }> = {
  '/': { title: 'Field Pricing', eyebrow: 'Start a quote or attach job files' },
  '/estimator': { title: 'Pricing Workspace', eyebrow: 'Build and review a live estimate' },
  '/estimates': { title: 'Saved Estimates', eyebrow: 'Resume and review recent pricing work' },
  '/pipeline': { title: 'Pipeline', eyebrow: 'Track open bids and won work' },
  '/suppliers': { title: 'Suppliers', eyebrow: 'Compare catalog pricing' },
  '/admin': { title: 'Admin', eyebrow: 'Manage pricing rules and templates' },
  '/blueprints': { title: 'Blueprints', eyebrow: 'Upload-led estimating entry point' },
  '/proposals': { title: 'Proposals', eyebrow: 'Customer-ready bid outputs' },
}
```

```tsx
// web/src/components/layout/MobileNav.tsx
'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { motion } from 'framer-motion'
import { MOBILE_TABS } from './nav'

export function MobileNav({ onOpenMore }: { onOpenMore: () => void }) {
  const pathname = usePathname()

  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-[color:var(--line)] bg-[color:var(--panel)]/95 backdrop-blur-xl lg:hidden">
      <div className="grid grid-cols-4 px-2 pb-[max(env(safe-area-inset-bottom),10px)] pt-2">
        {MOBILE_TABS.map(({ href, icon: Icon, label }) => {
          if (href === '#more') {
            return (
              <button
                key={label}
                type="button"
                onClick={onOpenMore}
                className="relative flex min-h-[58px] flex-col items-center justify-center gap-1 rounded-[1.25rem] text-[11px] font-semibold text-[color:var(--muted-ink)]"
              >
                <Icon size={18} />
                <span>{label}</span>
              </button>
            )
          }

          const active = pathname === href || (href !== '/' && pathname.startsWith(href + '/'))

          return (
            <Link
              key={href}
              href={href}
              className="relative flex min-h-[58px] flex-col items-center justify-center gap-1 rounded-[1.25rem] text-[11px] font-semibold"
            >
              {active && (
                <motion.span
                  layoutId="mobile-tab-indicator"
                  className="absolute inset-x-3 top-0 h-[3px] rounded-full bg-[color:var(--accent)]"
                />
              )}
              <Icon size={18} className={active ? 'text-[color:var(--accent-strong)]' : 'text-[color:var(--muted-ink)]'} />
              <span className={active ? 'text-[color:var(--ink)]' : 'text-[color:var(--muted-ink)]'}>{label}</span>
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
```

```tsx
// web/src/components/layout/Header.tsx
import { usePathname } from 'next/navigation'
import { Menu, MapPin } from 'lucide-react'
import { PAGE_META } from './nav'

export function Header({ onMenuClick }: { onMenuClick: () => void }) {
  const pathname = usePathname()
  const meta = PAGE_META[pathname] ?? (pathname.startsWith('/estimator') ? PAGE_META['/estimator'] : PAGE_META['/'])

  return (
    <header className="sticky top-0 z-20 border-b border-[color:var(--line)] bg-[color:var(--panel)]/95 backdrop-blur-xl">
      <div className="flex h-[68px] items-center gap-3 px-4">
        <button
          onClick={onMenuClick}
          className="rounded-[1rem] p-2 text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)] lg:hidden"
          aria-label="Open navigation"
        >
          <Menu size={18} />
        </button>
        <div className="min-w-0 flex-1">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[color:var(--muted-ink)]">{meta.eyebrow}</p>
          <h1 className="truncate text-lg font-semibold text-[color:var(--ink)]">{meta.title}</h1>
        </div>
        <div className="hidden items-center gap-2 rounded-full border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-3 py-1.5 sm:flex">
          <MapPin size={12} className="text-[color:var(--accent-strong)]" />
          <span className="text-xs font-medium text-[color:var(--muted-ink)]">DFW</span>
        </div>
        <div className="flex size-9 items-center justify-center rounded-full bg-[color:var(--accent-soft)] text-sm font-semibold text-[color:var(--accent-strong)]">
          E
        </div>
      </div>
    </header>
  )
}
```

```tsx
// web/src/components/layout/Sidebar.tsx
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { PRIMARY_NAV, SECONDARY_NAV } from './nav'

function SidebarContent({ onClose }: { onClose?: () => void }) {
  const pathname = usePathname()

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-[72px] items-center justify-between border-b border-[color:var(--line)] px-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[color:var(--muted-ink)]">PlumbPrice AI</p>
          <p className="text-sm font-semibold text-[color:var(--ink)]">Field Pricing Shell</p>
        </div>
        {onClose && (
          <button onClick={onClose} className="rounded-[1rem] p-2 text-[color:var(--muted-ink)] lg:hidden">
            <X size={16} />
          </button>
        )}
      </div>
      <nav className="flex-1 space-y-6 px-3 py-5">
        <div className="space-y-1">
          <p className="px-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-[color:var(--muted-ink)]">Workspace</p>
          {PRIMARY_NAV.map(({ href, icon: Icon, label }) => {
            const active = pathname === href || (href !== '/' && pathname.startsWith(href + '/'))
            return (
              <Link
                key={href}
                href={href}
                onClick={onClose}
                className={cn(
                  'flex items-center gap-3 rounded-[1.25rem] px-3 py-3 text-sm font-medium transition-colors',
                  active
                    ? 'bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]'
                    : 'text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)]',
                )}
              >
                <Icon size={16} />
                <span>{label}</span>
              </Link>
            )
          })}
        </div>
        <div className="space-y-1">
          <p className="px-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-[color:var(--muted-ink)]">Utilities</p>
          {SECONDARY_NAV.map(({ href, icon: Icon, label }) => {
            const active = pathname === href || pathname.startsWith(href + '/')
            return (
              <Link
                key={href}
                href={href}
                onClick={onClose}
                className={cn(
                  'flex items-center gap-3 rounded-[1.25rem] px-3 py-3 text-sm font-medium transition-colors',
                  active
                    ? 'bg-[color:var(--panel-strong)] text-[color:var(--ink)]'
                    : 'text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)]',
                )}
              >
                <Icon size={16} />
                <span>{label}</span>
              </Link>
            )
          })}
        </div>
      </nav>
    </div>
  )
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd web && npx vitest run src/components/layout/MobileNav.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/src/components/layout/nav.ts web/src/components/layout/MobileNav.test.tsx web/src/components/layout/MobileNav.tsx web/src/components/layout/Header.tsx web/src/components/layout/Sidebar.tsx
git commit -m "feat: add field-first shell navigation"
```

## Task 2: Replace the global shell theme and add the mobile More sheet

**Files:**
- Modify: `web/src/app/globals.css`
- Modify: `web/src/app/layout.tsx`
- Create: `web/src/components/layout/MoreSheet.tsx`
- Create: `web/src/components/layout/MoreSheet.test.tsx`
- Test: `web/src/components/layout/MoreSheet.test.tsx`

- [ ] **Step 1: Write the failing More sheet test**

```tsx
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { MoreSheet } from './MoreSheet'

vi.mock('next/link', () => ({
  default: ({ children, href, ...props }: any) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}))

describe('MoreSheet', () => {
  it('renders the utility destinations when opened', () => {
    render(<MoreSheet open onClose={() => {}} />)

    expect(screen.getByRole('link', { name: /suppliers/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /admin/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /blueprints/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /proposals/i })).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd web && npx vitest run src/components/layout/MoreSheet.test.tsx`
Expected: FAIL because `MoreSheet.tsx` does not exist yet.

- [ ] **Step 3: Implement the theme tokens, layout state, and More sheet**

```css
/* web/src/app/globals.css */
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --canvas: #f4efe6;
    --panel: rgba(255, 252, 247, 0.92);
    --panel-strong: #fffdf9;
    --ink: #1f2933;
    --muted-ink: #667085;
    --line: rgba(31, 41, 51, 0.08);
    --accent: #c26a32;
    --accent-strong: #8d4b24;
    --accent-soft: rgba(194, 106, 50, 0.14);
    --success-soft: rgba(38, 132, 94, 0.14);
    --danger-soft: rgba(191, 64, 64, 0.14);
    --shadow-lg: 0 24px 60px rgba(52, 40, 28, 0.14);
  }
}

html {
  -webkit-tap-highlight-color: transparent;
  -webkit-text-size-adjust: 100%;
}

body {
  min-height: 100dvh;
  color: var(--ink);
  font-family: 'IBM Plex Sans', 'Segoe UI', sans-serif;
  background:
    radial-gradient(circle at top left, rgba(194, 106, 50, 0.12), transparent 28%),
    linear-gradient(180deg, #f8f4ec 0%, #f1ebdf 100%);
  overscroll-behavior: none;
}

h1,
h2,
h3 {
  font-family: 'Fraunces', Georgia, serif;
}

@layer components {
  .shell-panel {
    @apply rounded-[1.75rem] border border-[color:var(--line)] bg-[color:var(--panel)] shadow-[var(--shadow-lg)];
  }

  .shell-card {
    @apply rounded-[1.5rem] border border-[color:var(--line)] bg-[color:var(--panel-strong)];
  }

  .shell-chip {
    @apply inline-flex items-center gap-2 rounded-full border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-3 py-1.5 text-xs font-medium text-[color:var(--muted-ink)];
  }

  .shell-input {
    @apply w-full rounded-[1.25rem] border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-4 py-3 text-sm text-[color:var(--ink)] placeholder:text-[color:var(--muted-ink)] focus:outline-none focus:ring-2 focus:ring-[color:var(--accent-soft)];
  }
}
```

```tsx
// web/src/components/layout/MoreSheet.tsx
'use client'

import Link from 'next/link'
import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'
import { MORE_LINKS } from './nav'

export function MoreSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40 bg-black/35 lg:hidden"
            onClick={onClose}
          />
          <motion.aside
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', stiffness: 320, damping: 32 }}
            className="fixed inset-x-0 bottom-0 z-50 rounded-t-[2rem] border-t border-[color:var(--line)] bg-[color:var(--panel)] px-4 pb-[max(env(safe-area-inset-bottom),16px)] pt-4 shadow-[var(--shadow-lg)] lg:hidden"
          >
            <div className="mb-4 flex items-center justify-between">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[color:var(--muted-ink)]">More</p>
                <h2 className="text-lg font-semibold text-[color:var(--ink)]">Utility pages</h2>
              </div>
              <button onClick={onClose} className="rounded-[1rem] p-2 text-[color:var(--muted-ink)] hover:bg-[color:var(--panel-strong)]">
                <X size={16} />
              </button>
            </div>
            <div className="grid gap-2">
              {MORE_LINKS.map(({ href, label, icon: Icon }) => (
                <Link
                  key={href}
                  href={href}
                  onClick={onClose}
                  className="flex items-center gap-3 rounded-[1.25rem] border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-4 py-3.5 text-sm font-medium text-[color:var(--ink)]"
                >
                  <Icon size={16} className="text-[color:var(--accent-strong)]" />
                  <span>{label}</span>
                </Link>
              ))}
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}
```

```tsx
// web/src/app/layout.tsx
'use client'

import type { ReactNode } from 'react'
import { useState } from 'react'
import { usePathname } from 'next/navigation'
import { AnimatePresence, motion } from 'framer-motion'
import { ToastProvider } from '@/components/ui/Toast'
import { Header } from '@/components/layout/Header'
import { Sidebar } from '@/components/layout/Sidebar'
import { MobileNav } from '@/components/layout/MobileNav'
import { MoreSheet } from '@/components/layout/MoreSheet'
import './globals.css'

export default function RootLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [moreOpen, setMoreOpen] = useState(false)

  return (
    <html lang="en">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
        <meta name="theme-color" content="#f4efe6" />
        <meta name="description" content="Mobile-first plumbing pricing workspace" />
        <title>PlumbPrice AI</title>
      </head>
      <body>
        <ToastProvider>
          <div className="flex min-h-dvh bg-transparent">
            <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
            <AnimatePresence>
              {sidebarOpen && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="fixed inset-0 z-30 bg-black/20 lg:hidden"
                  onClick={() => setSidebarOpen(false)}
                />
              )}
            </AnimatePresence>
            <div className="flex min-h-dvh flex-1 flex-col lg:ml-[272px]">
              <Header onMenuClick={() => setSidebarOpen(true)} />
              <main className="flex-1 overflow-x-hidden overflow-y-auto pb-[92px] lg:pb-0">
                <AnimatePresence mode="wait">
                  <motion.div
                    key={pathname}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -6 }}
                    transition={{ duration: 0.18 }}
                    className="min-h-full"
                  >
                    {children}
                  </motion.div>
                </AnimatePresence>
              </main>
            </div>
            <MobileNav onOpenMore={() => setMoreOpen(true)} />
            <MoreSheet open={moreOpen} onClose={() => setMoreOpen(false)} />
          </div>
        </ToastProvider>
      </body>
    </html>
  )
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd web && npx vitest run src/components/layout/MoreSheet.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/src/app/globals.css web/src/app/layout.tsx web/src/components/layout/MoreSheet.tsx web/src/components/layout/MoreSheet.test.tsx
git commit -m "feat: add warm app shell theme and mobile more sheet"
```

## Task 3: Build the launcher home screen with quick actions and recent jobs

**Files:**
- Modify: `web/src/app/page.tsx`
- Modify: `web/src/components/layout/Sidebar.tsx`
- Create: `web/src/components/workspace/PrimaryActionCard.tsx`
- Create: `web/src/components/workspace/RecentJobsList.tsx`
- Create: `web/src/components/workspace/LauncherHome.tsx`
- Create: `web/src/components/workspace/LauncherHome.test.tsx`
- Test: `web/src/components/workspace/LauncherHome.test.tsx`

- [ ] **Step 1: Write the failing launcher home test**

```tsx
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { LauncherHome } from './LauncherHome'

const push = vi.fn()

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push }),
}))

vi.mock('@/lib/api', () => ({
  estimatesApi: {
    list: vi.fn().mockResolvedValue({
      data: [
        {
          id: 42,
          title: 'Leak at Elm Street',
          job_type: 'service',
          status: 'draft',
          grand_total: 325,
          confidence_label: 'HIGH',
          county: 'Dallas',
          created_at: '2026-03-29T08:00:00Z',
        },
      ],
    }),
  },
}))

describe('LauncherHome', () => {
  it('shows the two primary actions and loads recent jobs', async () => {
    render(<LauncherHome />)

    expect(screen.getByRole('button', { name: /quick quote/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /upload job files/i })).toBeInTheDocument()
    expect(await screen.findByText(/leak at elm street/i)).toBeInTheDocument()
    expect(screen.getByText(/awaiting details/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd web && npx vitest run src/components/workspace/LauncherHome.test.tsx`
Expected: FAIL because `LauncherHome.tsx`, `PrimaryActionCard.tsx`, and `RecentJobsList.tsx` do not exist yet and `/` still renders the old estimator page directly.

- [ ] **Step 3: Implement the launcher home components and route**

```tsx
// web/src/components/workspace/PrimaryActionCard.tsx
'use client'

import { ArrowRight, type LucideIcon } from 'lucide-react'

export function PrimaryActionCard({
  title,
  description,
  icon: Icon,
  onClick,
}: {
  title: string
  description: string
  icon: LucideIcon
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="shell-panel flex w-full items-center justify-between gap-4 p-5 text-left transition-transform hover:-translate-y-0.5"
    >
      <div className="flex items-start gap-4">
        <div className="flex size-12 items-center justify-center rounded-[1.25rem] bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]">
          <Icon size={20} />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-[color:var(--ink)]">{title}</h2>
          <p className="mt-1 text-sm leading-6 text-[color:var(--muted-ink)]">{description}</p>
        </div>
      </div>
      <ArrowRight size={18} className="shrink-0 text-[color:var(--accent-strong)]" />
    </button>
  )
}
```

```tsx
// web/src/components/workspace/RecentJobsList.tsx
'use client'

import Link from 'next/link'
import { Clock3 } from 'lucide-react'

export interface RecentJobItem {
  id: number
  title: string
  statusLabel: string
  timeLabel: string
  totalLabel: string
  href: string
}

export function RecentJobsList({
  jobs,
  loading,
  compact = false,
}: {
  jobs: RecentJobItem[]
  loading: boolean
  compact?: boolean
}) {
  return (
    <section className={compact ? 'space-y-2' : 'shell-card p-4'}>
      {!compact && (
        <div className="mb-3 flex items-center justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[color:var(--muted-ink)]">Recent Jobs</p>
            <h2 className="text-lg font-semibold text-[color:var(--ink)]">Continue active work</h2>
          </div>
        </div>
      )}
      {loading ? (
        <div className="space-y-2">
          <div className="h-16 animate-pulse rounded-[1.25rem] bg-[color:var(--panel-strong)]" />
          <div className="h-16 animate-pulse rounded-[1.25rem] bg-[color:var(--panel-strong)]" />
        </div>
      ) : jobs.length === 0 ? (
        <div className="rounded-[1.25rem] border border-dashed border-[color:var(--line)] bg-[color:var(--panel-strong)] px-4 py-6 text-sm text-[color:var(--muted-ink)]">
          Your recent quotes will appear here after you price the first job.
        </div>
      ) : (
        <div className="space-y-2">
          {jobs.map(job => (
            <Link
              key={job.id}
              href={job.href}
              className="flex items-center justify-between gap-3 rounded-[1.25rem] border border-[color:var(--line)] bg-[color:var(--panel-strong)] px-4 py-3"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-[color:var(--ink)]">{job.title}</p>
                <div className="mt-1 flex items-center gap-2 text-xs text-[color:var(--muted-ink)]">
                  <span className="rounded-full bg-[color:var(--accent-soft)] px-2 py-0.5 text-[color:var(--accent-strong)]">{job.statusLabel}</span>
                  <span className="inline-flex items-center gap-1">
                    <Clock3 size={12} />
                    {job.timeLabel}
                  </span>
                </div>
              </div>
              <span className="shrink-0 text-sm font-semibold text-[color:var(--ink)]">{job.totalLabel}</span>
            </Link>
          ))}
        </div>
      )}
    </section>
  )
}
```

```tsx
// web/src/components/workspace/LauncherHome.tsx
'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { FileUp, MessageSquareText } from 'lucide-react'
import { formatDistanceToNowStrict } from 'date-fns'
import { estimatesApi, type EstimateListItem } from '@/lib/api'
import { formatCurrency } from '@/lib/utils'
import { PrimaryActionCard } from './PrimaryActionCard'
import { RecentJobsList, type RecentJobItem } from './RecentJobsList'

function normalizeRecentJobs(data: unknown): EstimateListItem[] {
  if (Array.isArray(data)) return data as EstimateListItem[]
  if (data && typeof data === 'object' && 'estimates' in data) {
    const payload = data as { estimates?: EstimateListItem[] }
    return payload.estimates ?? []
  }
  return []
}

function mapEstimateToRecentJob(item: EstimateListItem): RecentJobItem {
  const statusLabel = item.status === 'draft' ? 'Awaiting details' : item.status === 'sent' ? 'Estimate ready' : 'Recently updated'

  return {
    id: item.id,
    title: item.title || `${item.county} job`,
    statusLabel,
    timeLabel: `${formatDistanceToNowStrict(new Date(item.created_at))} ago`,
    totalLabel: item.grand_total > 0 ? formatCurrency(item.grand_total) : 'Draft',
    href: `/estimator?estimateId=${item.id}`,
  }
}

export function LauncherHome() {
  const router = useRouter()
  const [jobs, setJobs] = useState<RecentJobItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true

    estimatesApi
      .list({ limit: 5 })
      .then(response => {
        if (!active) return
        const list = normalizeRecentJobs(response.data)
        setJobs(list.slice(0, 5).map(mapEstimateToRecentJob))
      })
      .catch(() => {
        if (!active) return
        setJobs([])
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [])

  return (
    <div className="mx-auto flex min-h-full w-full max-w-3xl flex-col gap-6 px-4 py-5">
      <section className="shell-card p-5">
        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[color:var(--muted-ink)]">PlumbPrice AI</p>
        <h1 className="mt-2 text-3xl font-semibold text-[color:var(--ink)]">Start pricing from the field</h1>
        <p className="mt-3 max-w-xl text-sm leading-6 text-[color:var(--muted-ink)]">
          Launch a quick quote, attach job files, or jump back into the last estimate you touched.
        </p>
      </section>

      <div className="grid gap-4">
        <PrimaryActionCard
          title="Quick Quote"
          description="Start a repair price immediately from text and job details."
          icon={MessageSquareText}
          onClick={() => router.push('/estimator?entry=quick-quote')}
        />
        <PrimaryActionCard
          title="Upload Job Files"
          description="Use photos or PDFs as the starting point for the same pricing workspace."
          icon={FileUp}
          onClick={() => router.push('/estimator?entry=upload-job-files')}
        />
      </div>

      <RecentJobsList jobs={jobs} loading={loading} />
    </div>
  )
}
```

```tsx
// web/src/app/page.tsx
'use client'

import { LauncherHome } from '@/components/workspace/LauncherHome'

export default function Home() {
  return <LauncherHome />
}
```

```tsx
// web/src/components/layout/Sidebar.tsx
import { useEffect, useState } from 'react'
import { estimatesApi, type EstimateListItem } from '@/lib/api'
import { formatCurrency } from '@/lib/utils'
import { RecentJobsList, type RecentJobItem } from '@/components/workspace/RecentJobsList'

function mapEstimateToSidebarJob(item: EstimateListItem): RecentJobItem {
  return {
    id: item.id,
    title: item.title || `${item.county} job`,
    statusLabel: item.status === 'draft' ? 'Awaiting details' : 'Estimate ready',
    timeLabel: item.county,
    totalLabel: item.grand_total > 0 ? formatCurrency(item.grand_total) : 'Draft',
    href: `/estimator?estimateId=${item.id}`,
  }
}

function SidebarContent({ onClose }: { onClose?: () => void }) {
  const [recentJobs, setRecentJobs] = useState<RecentJobItem[]>([])
  const [loadingRecentJobs, setLoadingRecentJobs] = useState(true)

  useEffect(() => {
    let active = true

    estimatesApi
      .list({ limit: 4 })
      .then(response => {
        if (!active) return
        const payload = Array.isArray(response.data)
          ? response.data
          : ((response.data as { estimates?: EstimateListItem[] }).estimates ?? [])
        setRecentJobs(payload.slice(0, 4).map(mapEstimateToSidebarJob))
      })
      .catch(() => {
        if (active) setRecentJobs([])
      })
      .finally(() => {
        if (active) setLoadingRecentJobs(false)
      })

    return () => {
      active = false
    }
  }, [])

  return (
    <div className="hidden border-t border-[color:var(--line)] px-3 py-4 lg:block">
      <p className="mb-2 px-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-[color:var(--muted-ink)]">Recent Jobs</p>
      <RecentJobsList jobs={recentJobs} loading={loadingRecentJobs} compact />
    </div>
  )
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd web && npx vitest run src/components/workspace/LauncherHome.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/src/app/page.tsx web/src/components/layout/Sidebar.tsx web/src/components/workspace/PrimaryActionCard.tsx web/src/components/workspace/RecentJobsList.tsx web/src/components/workspace/LauncherHome.tsx web/src/components/workspace/LauncherHome.test.tsx
git commit -m "feat: add launcher home for field-first entry"
```

## Task 4: Recompose the estimator route into a unified workspace with a summary rail

**Files:**
- Create: `web/src/components/workspace/WorkspaceEntryBar.tsx`
- Create: `web/src/components/workspace/WorkspaceSummaryRail.tsx`
- Create: `web/src/components/workspace/WorkspaceSummaryRail.test.tsx`
- Modify: `web/src/components/estimator/EstimatorPage.tsx`
- Modify: `web/src/components/estimator/EstimateBreakdown.tsx`
- Modify: `web/src/components/estimator/ConfidenceBadge.tsx`
- Test: `web/src/components/workspace/WorkspaceSummaryRail.test.tsx`

- [ ] **Step 1: Write the failing summary rail test**

```tsx
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { WorkspaceSummaryRail } from './WorkspaceSummaryRail'

describe('WorkspaceSummaryRail', () => {
  it('shows the selected estimate totals and assumptions', () => {
    render(
      <WorkspaceSummaryRail
        county="Dallas"
        selectedEstimate={{
          id: 'a1',
          role: 'assistant',
          content: 'Estimate ready',
          confidence: 0.92,
          confidence_label: 'HIGH',
          assumptions: ['Two technicians required'],
          timestamp: new Date('2026-03-29T10:00:00Z'),
          estimate: {
            labor_total: 600,
            materials_total: 400,
            tax_total: 45,
            markup_total: 150,
            misc_total: 50,
            subtotal: 1200,
            grand_total: 1245,
            line_items: [],
          },
        }}
        mobileSheetOpen={false}
        onOpenMobileSheet={() => {}}
        onCloseMobileSheet={() => {}}
      />,
    )

    expect(screen.getByText(/recommended price/i)).toBeInTheDocument()
    expect(screen.getByText('$1,245')).toBeInTheDocument()
    expect(screen.getByText(/two technicians required/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd web && npx vitest run src/components/workspace/WorkspaceSummaryRail.test.tsx`
Expected: FAIL because `WorkspaceSummaryRail.tsx` does not exist yet.

- [ ] **Step 3: Implement the workspace entry bar, summary rail, and estimator shell updates**

```tsx
// web/src/components/workspace/WorkspaceEntryBar.tsx
'use client'

import { ChevronDown, FileUp, MapPin, MessageSquareText } from 'lucide-react'
import { cn } from '@/lib/utils'

export function WorkspaceEntryBar({
  county,
  counties,
  countyOpen,
  onToggleCounty,
  onSelectCounty,
  entryMode,
  onSelectEntryMode,
}: {
  county: string
  counties: string[]
  countyOpen: boolean
  onToggleCounty: () => void
  onSelectCounty: (county: string) => void
  entryMode: 'quick-quote' | 'upload-job-files'
  onSelectEntryMode: (mode: 'quick-quote' | 'upload-job-files') => void
}) {
  return (
    <section className="shell-card p-4">
      <div className="flex flex-wrap items-center gap-2">
        <button type="button" onClick={onToggleCounty} className="shell-chip">
          <MapPin size={14} className="text-[color:var(--accent-strong)]" />
          <span>{county} County</span>
          <ChevronDown size={14} className={cn(countyOpen && 'rotate-180')} />
        </button>
        {countyOpen && (
          <div className="flex flex-wrap gap-2">
            {counties.map(option => (
              <button
                key={option}
                type="button"
                onClick={() => onSelectCounty(option)}
                className={cn(
                  'rounded-full px-3 py-1.5 text-xs font-medium',
                  option === county ? 'bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]' : 'bg-[color:var(--panel-strong)] text-[color:var(--muted-ink)]',
                )}
              >
                {option}
              </button>
            ))}
          </div>
        )}
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <button
          type="button"
          onClick={() => onSelectEntryMode('quick-quote')}
          className={cn(
            'shell-card flex items-start gap-3 p-4 text-left',
            entryMode === 'quick-quote' && 'border-[color:var(--accent)] bg-[color:var(--accent-soft)]',
          )}
        >
          <div className="mt-0.5 rounded-[1rem] bg-[color:var(--panel)] p-2 text-[color:var(--accent-strong)]">
            <MessageSquareText size={16} />
          </div>
          <div>
            <p className="text-sm font-semibold text-[color:var(--ink)]">Quick Quote</p>
            <p className="mt-1 text-xs leading-5 text-[color:var(--muted-ink)]">Ask for a service price and review the estimate artifact.</p>
          </div>
        </button>
        <button
          type="button"
          onClick={() => onSelectEntryMode('upload-job-files')}
          className={cn(
            'shell-card flex items-start gap-3 p-4 text-left',
            entryMode === 'upload-job-files' && 'border-[color:var(--accent)] bg-[color:var(--accent-soft)]',
          )}
        >
          <div className="mt-0.5 rounded-[1rem] bg-[color:var(--panel)] p-2 text-[color:var(--accent-strong)]">
            <FileUp size={16} />
          </div>
          <div>
            <p className="text-sm font-semibold text-[color:var(--ink)]">Upload Job Files</p>
            <p className="mt-1 text-xs leading-5 text-[color:var(--muted-ink)]">Keep the same workspace, but start from photos and PDFs.</p>
          </div>
        </button>
      </div>
    </section>
  )
}
```

```tsx
// web/src/components/workspace/WorkspaceSummaryRail.tsx
'use client'

import { AnimatePresence, motion } from 'framer-motion'
import { ChevronUp, DollarSign } from 'lucide-react'
import { formatCurrency } from '@/lib/utils'
import type { ChatMessage } from '@/types'
import { EstimateBreakdown } from '@/components/estimator/EstimateBreakdown'

export function WorkspaceSummaryRail({
  county,
  selectedEstimate,
  mobileSheetOpen,
  onOpenMobileSheet,
  onCloseMobileSheet,
}: {
  county: string
  selectedEstimate: ChatMessage | null
  mobileSheetOpen: boolean
  onOpenMobileSheet: () => void
  onCloseMobileSheet: () => void
}) {
  const estimate = selectedEstimate?.estimate

  return (
    <>
      <aside className="hidden w-[360px] shrink-0 lg:block">
        <div className="sticky top-[84px] px-4 pb-4">
          <div className="shell-panel min-h-[420px] overflow-hidden">
            {estimate ? (
              <EstimateBreakdown
                estimate={estimate}
                confidenceLabel={selectedEstimate?.confidence_label || 'HIGH'}
                confidenceScore={selectedEstimate?.confidence || 0}
                assumptions={selectedEstimate?.assumptions || []}
                county={county}
              />
            ) : (
              <div className="flex h-full min-h-[420px] flex-col items-center justify-center gap-3 px-8 text-center">
                <div className="flex size-12 items-center justify-center rounded-[1.25rem] bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]">
                  <DollarSign size={18} />
                </div>
                <p className="text-base font-semibold text-[color:var(--ink)]">Estimate summary</p>
                <p className="text-sm leading-6 text-[color:var(--muted-ink)]">Ask a question or attach job files to populate totals, confidence, and assumptions.</p>
              </div>
            )}
          </div>
        </div>
      </aside>

      <AnimatePresence>
        {estimate && !mobileSheetOpen && (
          <motion.button
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            onClick={onOpenMobileSheet}
            className="fixed bottom-[88px] right-4 z-30 rounded-full bg-[color:var(--accent)] px-4 py-3 text-sm font-semibold text-white shadow-[var(--shadow-lg)] lg:hidden"
          >
            {formatCurrency(estimate.grand_total)}
          </motion.button>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {estimate && mobileSheetOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40 bg-black/30 lg:hidden"
              onClick={onCloseMobileSheet}
            />
            <motion.div
              initial={{ y: '100%' }}
              animate={{ y: 0 }}
              exit={{ y: '100%' }}
              transition={{ type: 'spring', stiffness: 320, damping: 32 }}
              className="fixed inset-x-0 bottom-0 z-50 overflow-hidden rounded-t-[2rem] border-t border-[color:var(--line)] bg-[color:var(--panel)] lg:hidden"
              style={{ maxHeight: '86dvh', paddingBottom: 'max(env(safe-area-inset-bottom),16px)' }}
            >
              <div className="flex items-center justify-between px-5 py-4">
                <p className="text-base font-semibold text-[color:var(--ink)]">Estimate summary</p>
                <button onClick={onCloseMobileSheet} className="rounded-[1rem] p-2 text-[color:var(--muted-ink)]">
                  <ChevronUp size={16} />
                </button>
              </div>
              <div className="max-h-[72dvh] overflow-y-auto">
                <EstimateBreakdown
                  estimate={estimate}
                  confidenceLabel={selectedEstimate?.confidence_label || 'HIGH'}
                  confidenceScore={selectedEstimate?.confidence || 0}
                  assumptions={selectedEstimate?.assumptions || []}
                  county={county}
                  compact
                />
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  )
}
```

```tsx
// web/src/components/estimator/EstimatorPage.tsx
'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { motion } from 'framer-motion'
import { Send } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { chatApi } from '@/lib/api'
import { useToast } from '@/components/ui/Toast'
import type { ChatMessage } from '@/types'
import { WorkspaceEntryBar } from '@/components/workspace/WorkspaceEntryBar'
import { WorkspaceSummaryRail } from '@/components/workspace/WorkspaceSummaryRail'

const COUNTIES = ['Dallas', 'Tarrant', 'Collin', 'Denton', 'Rockwall', 'Parker']

export function EstimatorPage() {
  const searchParams = useSearchParams()
  const entryFromUrl = searchParams.get('entry') === 'upload-job-files' ? 'upload-job-files' : 'quick-quote'
  const { success } = useToast()
  const [entryMode, setEntryMode] = useState<'quick-quote' | 'upload-job-files'>(entryFromUrl)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [county, setCounty] = useState('Dallas')
  const [countyOpen, setCountyOpen] = useState(false)
  const [selectedEstimate, setSelectedEstimate] = useState<ChatMessage | null>(null)
  const [sheetOpen, setSheetOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => setEntryMode(entryFromUrl), [entryFromUrl])
  useEffect(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), [messages, loading])

  const sendMessage = useCallback(async () => {
    const message = input.trim()
    if (!message || loading) return

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: message,
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setError(null)
    setLoading(true)

    try {
      const { data } = await chatApi.price({ message, county })
      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: data.answer,
        estimate: data.estimate,
        confidence: data.confidence,
        confidence_label: data.confidence_label,
        assumptions: data.assumptions,
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, assistantMessage])
      if (data.estimate) {
        setSelectedEstimate(assistantMessage)
        success('Estimate ready')
      }
    } catch {
      setError('Could not reach the pricing service. Try again or switch to Upload Job Files if you are starting from documents.')
    } finally {
      setLoading(false)
    }
  }, [county, input, loading, success])

  return (
    <div className="mx-auto flex min-h-full w-full max-w-[1440px] gap-6 px-4 py-5 lg:items-start">
      <div className="min-w-0 flex-1 space-y-4">
        <WorkspaceEntryBar
          county={county}
          counties={COUNTIES}
          countyOpen={countyOpen}
          onToggleCounty={() => setCountyOpen(open => !open)}
          onSelectCounty={option => {
            setCounty(option)
            setCountyOpen(false)
          }}
          entryMode={entryMode}
          onSelectEntryMode={setEntryMode}
        />

        {entryMode === 'upload-job-files' && (
          <section className="shell-card p-4">
            <p className="text-sm font-semibold text-[color:var(--ink)]">Upload intake</p>
            <p className="mt-2 text-sm leading-6 text-[color:var(--muted-ink)]">
              File-led pricing is visible now. Wire the actual camera, photo library, and PDF upload actions next, but keep this state honest until the backend hookup lands.
            </p>
          </section>
        )}

        {error && (
          <section className="shell-card border border-red-200 bg-[color:var(--panel-strong)] p-4">
            <p className="text-sm font-semibold text-red-700">Pricing request failed</p>
            <p className="mt-2 text-sm leading-6 text-[color:var(--muted-ink)]">{error}</p>
          </section>
        )}

        <section className="shell-panel flex min-h-[520px] flex-col overflow-hidden">
          <div className="flex-1 space-y-4 overflow-y-auto p-4">
            {messages.length === 0 ? (
              <div className="shell-card p-5">
                <h2 className="text-2xl font-semibold text-[color:var(--ink)]">Ask for a price</h2>
                <p className="mt-3 text-sm leading-6 text-[color:var(--muted-ink)]">
                  Start with a repair question, then inspect confidence, assumptions, and line items in the summary rail.
                </p>
              </div>
            ) : (
              messages.map(message => (
                <motion.div key={message.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}>
                  <div className={message.role === 'user' ? 'ml-auto max-w-[85%] rounded-[1.5rem] bg-[color:var(--accent)] px-4 py-3 text-white' : 'shell-card max-w-[90%] px-4 py-3'}>
                    {message.role === 'assistant' ? <ReactMarkdown>{message.content}</ReactMarkdown> : message.content}
                  </div>
                </motion.div>
              ))
            )}
            <div ref={bottomRef} />
          </div>
          <div className="border-t border-[color:var(--line)] bg-[color:var(--panel)] px-4 py-4">
            <div className="flex items-end gap-3">
              <textarea
                ref={inputRef}
                value={input}
                onChange={event => setInput(event.target.value)}
                onKeyDown={event => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault()
                    void sendMessage()
                  }
                }}
                placeholder="Ask a pricing question"
                rows={1}
                className="shell-input min-h-[52px] resize-none"
              />
              <button type="button" onClick={() => void sendMessage()} className="flex size-[52px] items-center justify-center rounded-[1.25rem] bg-[color:var(--accent)] text-white">
                <Send size={18} />
              </button>
            </div>
          </div>
        </section>
      </div>

      <WorkspaceSummaryRail
        county={county}
        selectedEstimate={selectedEstimate}
        mobileSheetOpen={sheetOpen}
        onOpenMobileSheet={() => setSheetOpen(true)}
        onCloseMobileSheet={() => setSheetOpen(false)}
      />
    </div>
  )
}
```

```tsx
// web/src/components/estimator/ConfidenceBadge.tsx
import { CheckCircle2, AlertCircle, XCircle } from 'lucide-react'
import { cn, getConfidenceColor } from '@/lib/utils'

export function ConfidenceBadge({ label, score, size = 'sm' }: { label: string; score: number; size?: 'sm' | 'md' }) {
  const Icon = label === 'HIGH' ? CheckCircle2 : label === 'MEDIUM' ? AlertCircle : XCircle

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border font-medium',
        size === 'sm' ? 'px-2.5 py-1 text-xs' : 'px-3 py-1.5 text-sm',
        getConfidenceColor(label),
      )}
    >
      <Icon className={size === 'sm' ? 'h-3.5 w-3.5' : 'h-4 w-4'} />
      {label} · {Math.round(score * 100)}%
    </span>
  )
}
```

```tsx
// web/src/components/estimator/EstimateBreakdown.tsx
<div className={cn('shrink-0 border-b border-[color:var(--line)] bg-[color:var(--panel-strong)]', pad)}>
  <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[color:var(--muted-ink)]">Recommended Price</div>
  <div className={cn('mt-3 font-semibold leading-none text-[color:var(--ink)]', compact ? 'text-4xl' : 'text-5xl')}>
    {formatCurrency(estimate.grand_total)}
  </div>
</div>
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd web && npx vitest run src/components/workspace/WorkspaceSummaryRail.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/src/components/workspace/WorkspaceEntryBar.tsx web/src/components/workspace/WorkspaceSummaryRail.tsx web/src/components/workspace/WorkspaceSummaryRail.test.tsx web/src/components/estimator/EstimatorPage.tsx web/src/components/estimator/EstimateBreakdown.tsx web/src/components/estimator/ConfidenceBadge.tsx
git commit -m "feat: recompose estimator into unified workspace"
```

## Task 5: Roll the new shell system through support pages

**Files:**
- Create: `web/src/components/layout/PageIntro.tsx`
- Create: `web/src/components/estimates/EstimatesListPage.test.tsx`
- Modify: `web/src/components/estimates/EstimatesListPage.tsx`
- Modify: `web/src/components/pipeline/PipelinePage.tsx`
- Modify: `web/src/components/suppliers/SuppliersPage.tsx`
- Modify: `web/src/components/admin/AdminPage.tsx`
- Modify: `web/src/app/blueprints/page.tsx`
- Modify: `web/src/app/proposals/page.tsx`
- Test: `web/src/components/estimates/EstimatesListPage.test.tsx`

- [ ] **Step 1: Write the failing saved estimates page test**

```tsx
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { EstimatesListPage } from './EstimatesListPage'

const push = vi.fn()

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push }),
}))

vi.mock('@/lib/api', () => ({
  api: {
    get: vi.fn().mockResolvedValue({ data: [] }),
    delete: vi.fn(),
  },
}))

vi.mock('@/components/ui/Toast', () => ({
  useToast: () => ({
    success: vi.fn(),
    error: vi.fn(),
  }),
}))

describe('EstimatesListPage', () => {
  it('shows the new saved estimates intro and quick quote action', async () => {
    render(<EstimatesListPage />)

    expect(await screen.findByRole('heading', { name: /saved estimates/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /quick quote/i })).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd web && npx vitest run src/components/estimates/EstimatesListPage.test.tsx`
Expected: FAIL because the current page still uses the old dark top bar and does not render the new intro copy or action label.

- [ ] **Step 3: Implement the shared page intro and support-page shell adoption**

```tsx
// web/src/components/layout/PageIntro.tsx
import type { ReactNode } from 'react'
import { type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

export function PageIntro({
  icon: Icon,
  eyebrow,
  title,
  description,
  actions,
  className,
}: {
  icon: LucideIcon
  eyebrow: string
  title: string
  description: string
  actions?: ReactNode
  className?: string
}) {
  return (
    <section className={cn('shell-panel p-5', className)}>
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="flex items-start gap-4">
          <div className="flex size-12 items-center justify-center rounded-[1.25rem] bg-[color:var(--accent-soft)] text-[color:var(--accent-strong)]">
            <Icon size={18} />
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[color:var(--muted-ink)]">{eyebrow}</p>
            <h1 className="mt-2 text-3xl font-semibold text-[color:var(--ink)]">{title}</h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-[color:var(--muted-ink)]">{description}</p>
          </div>
        </div>
        {actions}
      </div>
    </section>
  )
}
```

```tsx
// web/src/components/estimates/EstimatesListPage.tsx
import { FileText, Plus } from 'lucide-react'
import { PageIntro } from '@/components/layout/PageIntro'

<div className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-4 py-5">
  <PageIntro
    icon={FileText}
    eyebrow="Saved Estimates"
    title="Saved Estimates"
    description="Review finished pricing work, reopen drafts, and move back into the workspace with one tap."
    actions={
      <button onClick={() => router.push('/estimator?entry=quick-quote')} className="rounded-[1.25rem] bg-[color:var(--accent)] px-4 py-3 text-sm font-semibold text-white">
        <span className="inline-flex items-center gap-2">
          <Plus size={16} />
          Quick Quote
        </span>
      </button>
    }
  />
</div>
```

```tsx
// web/src/components/pipeline/PipelinePage.tsx
<div className="mx-auto flex w-full max-w-7xl flex-col gap-4 px-4 py-5">
  <PageIntro
    icon={BriefcaseBusiness}
    eyebrow="Pipeline"
    title="Pipeline"
    description="Track open pricing work, estimate sent status, and won jobs without competing with the workspace."
  />
</div>
```

```tsx
// web/src/components/suppliers/SuppliersPage.tsx
<div className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-4 py-5">
  <PageIntro
    icon={Package}
    eyebrow="Suppliers"
    title="Supplier Pricing"
    description="Compare vendor catalog pricing inside the same warm shell system used by the workspace."
  />
</div>
```

```tsx
// web/src/components/admin/AdminPage.tsx
<div className="mx-auto flex w-full max-w-5xl flex-col gap-4 px-4 py-5">
  <PageIntro
    icon={BarChart3}
    eyebrow="Admin"
    title="Pricing Rules"
    description="Manage labor templates, markup rules, and reporting without dropping back into the old dashboard chrome."
  />
</div>
```

```tsx
// web/src/app/blueprints/page.tsx
<div className="mx-auto flex w-full max-w-4xl flex-col gap-4 px-4 py-5">
  <PageIntro
    icon={Layers}
    eyebrow="Blueprints"
    title="Blueprint Intake"
    description="Keep blueprint-led estimating inside the new shell, even before the full upload pipeline is wired."
  />
</div>
```

```tsx
// web/src/app/proposals/page.tsx
<div className="mx-auto flex w-full max-w-4xl flex-col gap-4 px-4 py-5">
  <PageIntro
    icon={FileOutput}
    eyebrow="Proposals"
    title="Proposal Outputs"
    description="Expose proposal generation as a utility destination that matches the new shell system."
  />
</div>
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd web && npx vitest run src/components/estimates/EstimatesListPage.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/src/components/layout/PageIntro.tsx web/src/components/estimates/EstimatesListPage.test.tsx web/src/components/estimates/EstimatesListPage.tsx web/src/components/pipeline/PipelinePage.tsx web/src/components/suppliers/SuppliersPage.tsx web/src/components/admin/AdminPage.tsx web/src/app/blueprints/page.tsx web/src/app/proposals/page.tsx
git commit -m "feat: apply app shell system to support pages"
```

## Task 6: Run full frontend verification and create the final feature commit

**Files:**
- Modify: all files touched in Tasks 1-5
- Test: complete frontend verification commands

- [ ] **Step 1: Run the focused test suite**

Run:

```bash
cd web && npx vitest run \
  src/components/layout/MobileNav.test.tsx \
  src/components/layout/MoreSheet.test.tsx \
  src/components/workspace/LauncherHome.test.tsx \
  src/components/workspace/WorkspaceSummaryRail.test.tsx \
  src/components/estimates/EstimatesListPage.test.tsx
```

Expected: PASS

- [ ] **Step 2: Run lint**

Run: `cd web && npm run lint`
Expected: PASS with `0` errors and `0` warnings

- [ ] **Step 3: Run the production build**

Run: `cd web && npm run build`
Expected: PASS with a successful Next.js production build

- [ ] **Step 4: Commit the completed shell refresh**

```bash
git add web/src/app/globals.css web/src/app/layout.tsx web/src/app/page.tsx web/src/app/blueprints/page.tsx web/src/app/proposals/page.tsx web/src/components/layout web/src/components/workspace web/src/components/estimator/EstimatorPage.tsx web/src/components/estimator/EstimateBreakdown.tsx web/src/components/estimator/ConfidenceBadge.tsx web/src/components/estimates/EstimatesListPage.tsx web/src/components/pipeline/PipelinePage.tsx web/src/components/suppliers/SuppliersPage.tsx web/src/components/admin/AdminPage.tsx
git commit -m "feat: refresh app shell for mobile-first pricing"
```
