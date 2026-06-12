# UI Enhancement Plan — PlumbPrice AI

> **Version**: 1.0 — June 2026
> **Scope**: Frontend (`web/`) — Next.js 15, Tailwind CSS 3, Framer Motion, Radix UI
> **Theme**: Warm earthy palette with burnt rust accent

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current State Assessment](#2-current-state-assessment)
3. [Priority Matrix](#3-priority-matrix)
4. [Phase 1 — Design System Consistency](#4-phase-1--design-system-consistency)
5. [Phase 2 — Navigation & Layout](#5-phase-2--navigation--layout)
6. [Phase 3 — Visual Polish & Micro-interactions](#6-phase-3--visual-polish--micro-interactions)
7. [Phase 4 — Loading, Empty, Error States](#7-phase-4--loading-empty-error-states)
8. [Phase 5 — Responsive & Mobile Optimization](#8-phase-5--responsive--mobile-optimization)
9. [Phase 6 — Accessibility & Performance](#9-phase-6--accessibility--performance)
10. [Measurement & Verification](#10-measurement--verification)

---

## 1. Executive Summary

The PlumbPrice frontend has a well-architected design system with thoughtful tokens, strong accessibility patterns, and tasteful motion design. However, several key surfaces — auth pages, error boundaries, admin pages — haven't been migrated to the v5.1 design tokens and use hardcoded colors, creating visual inconsistency. There are also gaps in loading states, page transitions, and responsive polish.

This plan addresses **6 priority phases** with concrete, scoped changes. Each item includes the specific files to modify, the approach, and the expected outcome.

---

## 2. Current State Assessment

### Strengths
- **Comprehensive design token system** — HSL-based custom properties with light/dark variants organized by category
- **Rich component library** — 30+ well-crafted UI primitives in `components/ui/`
- **Consistent page composition** — `PageShell → PageHeader → Section → Content` pattern works well
- **Tasteful motion** — Framer Motion with short durations, spring physics, and `prefers-reduced-motion` support
- **Accessibility foundations** — Skip-to-main, RouteAnnouncer, focus-visible rings, aria attributes
- **Responsive scaffolding** — Sidebar/hamburger/MobileNav breakpoints, safe-area insets, `clamp()` spacing
- **Performance discipline** — Lazy-loaded dialogs, optimized package imports, bundle analysis

### High-Priority Issues
| Issue | Impacted Files | Severity |
|---|---|---|
| **Hardcoded colors in auth pages** — Login, forgot/reset password use `#060606`, `zinc-*` instead of `--canvas`, `--panel`, `--ink` etc. | `LoginForm.tsx`, `ForgotPasswordForm.tsx`, `ResetPasswordForm.tsx` | 🔴 High |
| **Hardcoded colors in error/not-found pages** — Same pattern, plus blue accent instead of burnt rust | `error.tsx`, `not-found.tsx` | 🔴 High |
| **Brand color mismatch** — Blue (`from-blue-500`) used in auth/error/404 instead of burnt rust accent | `LoginForm.tsx`, `error.tsx`, `not-found.tsx` | 🟡 Medium |
| **Two different page header components** — `PageHeader` (shell) and `PageIntro` (admin) serve same purpose | `PageHeader.tsx`, `PageIntro.tsx` | 🟡 Medium |
| **No `loading.tsx` files anywhere** — No full-page skeleton loaders during route transitions | Entire `app/` directory | 🟡 Medium |
| **Admin page bypasses `PageShell`** — Uses hardcoded `max-w-4xl` and `PageIntro` | `AdminPage.tsx` | 🟡 Medium |

### Medium-Priority Issues
| Issue | Impacted Files | Severity |
|---|---|---|
| Root layout body uses `--background` (legacy) instead of `--canvas` | `layout.tsx` | 🟢 Low |
| Button component uses hardcoded shadow instead of `--shadow-md` token | `Button.tsx` | 🟢 Low |
| Sidebar widths hardcoded (64px, 248px) instead of reading `--sidebar-rail` / `--sidebar-expanded` | `Sidebar.tsx` | 🟢 Low |
| Estimator components are very long (350-450 lines) | `EstimatorPage.tsx`, `EstimatorPageV3.tsx` | 🟢 Low |
| Legacy component classes (`glass`, `card`, `btn-primary`, etc.) coexist with v5.1 shell classes | `globals.css` | 🟢 Low |
| No page transition animations between routes | `ClientLayout.tsx` | 🟢 Low |

---

## 3. Priority Matrix

| Phase | Effort | Impact | Dependencies |
|---|---|---|---|
| **Phase 1: Design System Consistency** | Medium | High | None |
| **Phase 2: Navigation & Layout** | Low | Medium | Phase 1 |
| **Phase 3: Visual Polish & Micro-interactions** | Medium | Medium | Phase 1 |
| **Phase 4: Loading, Empty, Error States** | Medium | High | None |
| **Phase 5: Responsive & Mobile Optimization** | Low | Medium | Phase 1 |
| **Phase 6: Accessibility & Performance** | Low | Medium | None |

---

## 4. Phase 1 — Design System Consistency

### 4.1 Migrate Auth Pages to Design Tokens

**Files**: `web/src/components/auth/LoginForm.tsx`, `ForgotPasswordForm.tsx`, `ResetPasswordForm.tsx`, `AcceptInviteForm.tsx`

**Current State**: All auth forms use hardcoded colors:
```tsx
// ❌ Current — hardcoded
<div className="min-h-screen bg-[#060606]" />
<div className="bg-[#0f0f0f] border-white/[0.08]" />
<span className="text-zinc-400" />
```

**Target**: Replace with design tokens:
```tsx
// ✅ Target — token-driven
<div className="min-h-screen" style={{ background: 'var(--canvas)' }} />
<div className="shell-panel" />
<span className="text-[color:var(--muted-ink)]" />
```

**Changes**:
1. Replace all `#060606` and `#0f0f0f` backgrounds with `var(--canvas)` and `var(--panel)`
2. Replace `zinc-*` text colors with `var(--ink)`, `var(--ink-secondary)`, `var(--muted-ink)`
3. Replace `border-white/[0.08]` with `var(--line)`
4. Replace blue gradient brand elements with burnt rust gradient
5. Add dark mode support (`.dark` variant) alongside light mode
6. Use `cn()` helper consistently for conditional classes

**Verification**: Auth pages render correctly in both light and dark mode without any hardcoded color values.

---

### 4.2 Migrate Error & Not-Found Pages to Design Tokens

**Files**: `web/src/app/error.tsx`, `web/src/app/not-found.tsx`

**Current State**: Same hardcoded dark color pattern as auth pages. Blue accent on buttons. No design token usage.

**Changes**:
1. Replace hardcoded background colors with `var(--canvas)`, `var(--panel)`
2. Replace blue "Go Home" / "Back to Home" buttons with burnt rust accent
3. Add proper dark/light mode support with design tokens
4. Ensure the error details `<details>` element respects the color system
5. Keep the existing animation but ensure it respects `prefers-reduced-motion`

**Verification**: Error and 404 pages render in both themes. Buttons use `var(--accent)` not blue.

---

### 4.3 Unify Page Header Components

**Files**: `web/src/components/layout/PageIntro.tsx`, `web/src/components/layout/shell/PageHeader.tsx`

**Current State**: Two components with similar purpose:
- `PageHeader` — used by shell pattern, takes `eyebrow`, `title`, `description`, `actions`
- `PageIntro` — used by admin pages, takes `title`, `description`, `actions` (no eyebrow)

**Recommended Approach**: Deprecate `PageIntro`. Add an optional `eyebrow` prop to `PageHeader` (it already has one). Update all `PageIntro` imports to use `PageHeader` instead.

**Changes**:
1. Add a deprecation comment to `PageIntro.tsx`
2. Update `AdminPage.tsx` to use `PageShell + PageHeader` instead of `PageIntro`
3. Update all other `PageIntro` consumers to use `PageHeader`

**Verification**: No remaining imports of `PageIntro`. Admin pages use the same shell pattern as every other page.

---

### 4.4 Convert Admin Page to Use PageShell

**File**: `web/src/components/admin/AdminPage.tsx`

**Current State**: Uses `max-w-4xl` wrapper and `PageIntro` instead of `PageShell + PageHeader`.

**Changes**:
1. Replace `max-w-4xl mx-auto` with `<PageShell width="narrow">`
2. Replace `PageIntro` with `<PageHeader eyebrow="Admin" title="Admin" description="..." />`
3. Ensure tabs layout still works with the new shell wrapper

**Verification**: Admin page looks identical but uses the same structural pattern as all other pages.

---

### 4.5 Fix Token Reference Gaps

**Files**: Various

**Changes**:
1. **Root layout** (`layout.tsx`): Change `bg-[hsl(var(--background))]` to use `var(--canvas)` or remove (body already has background in `globals.css`)
2. **Button.tsx**: Replace `shadow-[0_4px_12px_hsl(var(--accent-hsl)/0.28)]` with `shadow-elev-2` or similar token
3. **Sidebar.tsx**: Replace hardcoded `64` / `248` with `var(--sidebar-rail)` / `var(--sidebar-expanded)` via CSS or `getComputedStyle()`

**Verification**: No hardcoded color/shadow/width values that have a corresponding design token.

---

## 5. Phase 2 — Navigation & Layout

### 5.1 Sidebar Enhancements

**File**: `web/src/components/layout/Sidebar.tsx`

**Changes**:
1. Add collapse/expand animation with smoother spring physics (match `--ease-spring` token)
2. Show active section indicator with stronger visual weight (increase accent bar width from 3px to 4px)
3. Add keyboard navigation: `ArrowUp/Down` to move between items, `Enter` to select
4. Consider adding collapsible nav sections for long-term scalability

### 5.2 Mobile Navigation Polish

**File**: `web/src/components/layout/MobileNav.tsx`

**Changes**:
1. Add haptic feedback on tab press (via existing `lib/haptics.ts`)
2. Ensure the indicator animation uses layoutId for shared layout animations
3. Review safe-area bottom padding on devices with home indicators

### 5.3 Page Transition Animations

**File**: `web/src/components/layout/ClientLayout.tsx`

**Current State**: Basic opacity + y-shift transition on page change.

**Changes**:
1. Enhance the `AnimatePresence` page transition with a more polished effect:
   - Light mode: subtle scale + opacity (0.98 → 1, 0 → 1)
   - Dark mode: slight fade only (avoids flash)
2. Duration: 150-200ms (respects `--duration-normal`)
3. Ensure `prefers-reduced-motion` disables entirely
4. Consider using `useReducedMotion()` hook

---

## 6. Phase 3 — Visual Polish & Micro-interactions

### 6.1 Card & Panel Hover States

**Files**: Apply across `shell-card`, `shell-panel` usage

**Changes**:
1. Add subtle lift effect on hover (`translateY(-2px)`) with shadow elevation bump
2. Use `--ease-out` timing, 200ms duration
3. Ensure interactive cards have `cursor-pointer`

### 6.2 Form Input Focus States

**Files**: All form inputs across the app

**Current State**: `shell-input` has a 3px accent-soft box-shadow on focus.

**Changes**:
1. Ensure ALL inputs (native `<input>`, `<select>`, `<textarea>`) use the same focus pattern
2. Add a subtle scale transform (1.01) on focus for non-touch devices
3. Ensure `:focus-visible` only shows ring on keyboard navigation

### 6.3 Button Consistency Pass

**Files**: Audit all button usage across the app

**Changes**:
1. Ensure all buttons use the `Button` component (or `shell-button-*` classes) — no raw `<button>` with custom styling
2. Standardize loading states across all action buttons
3. Ensure disabled states are visually consistent

### 6.4 Empty State Enhancement

**File**: `web/src/components/ui/EmptyState.tsx`

**Changes**:
1. Add illustration or icon animation (gentle float or pulse)
2. Ensure all data pages use consistent empty state messaging
3. Add contextual action buttons (e.g., "Create first estimate")

### 6.5 Data Visualization Polish

**Files**: `BarChart.tsx`, `DonutChart.tsx`, KPI strip, stat cards

**Changes**:
1. Add hover tooltips on chart segments showing exact values
2. Add entrance animations (staggered, spring-based)
3. Ensure chart colors use the design system palette
4. Add responsive behavior for small screens

---

## 7. Phase 4 — Loading, Empty, Error States

### 7.1 Add Route-Level Loading Boundaries

**Files**: Create `loading.tsx` at key route levels

**Priority Routes** (add `loading.tsx` to each):
- `/estimates` — Skeleton table/card layout matching the actual content
- `/pipeline` — Skeleton Kanban board (3 columns with card skeletons)
- `/analytics` — Skeleton chart areas
- `/blueprints` — Skeleton grid
- `/suppliers` — Skeleton data table
- `/sessions` — Skeleton list
- `/documents` — Skeleton grid
- `/proposals` — Skeleton cards

**Pattern**:
```tsx
// app/estimates/loading.tsx
export default function EstimatesLoading() {
  return (
    <PageShell>
      <PageHeader.Skeleton />
      <div className="space-y-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-24 rounded-[1.25rem]" />
        ))}
      </div>
    </PageShell>
  )
}
```

### 7.2 Review Error Boundaries

**Files**: Current `error.tsx`, `ErrorState.tsx`, `ErrorBoundary.tsx`

**Changes**:
1. Ensure all data-fetching pages have inline error states (already good pattern with `ErrorState.tsx`)
2. Add retry logic with exponential backoff for transient failures
3. Ensure error messages are user-friendly (not raw API errors)

### 7.3 Offline State Enhancement

**Files**: `OfflineBanner.tsx`, `OfflineBanner` usage

**Changes**:
1. Ensure the offline banner is visible but not intrusive
2. Show queue status (X pending mutations) when outbox has items
3. Add optimistic UI updates for offline mutations that show pending state
4. Ensure offline pages show cached data where available

---

## 8. Phase 5 — Responsive & Mobile Optimization

### 8.1 Estimator Mobile Layout

**Files**: `EstimatorPage.tsx`, `EstimatorPageV3.tsx`

**Changes**:
1. The right-side summary rail (360px) should collapse into a bottom sheet or collapsible panel on mobile
2. Chat input should be pinned to the bottom with keyboard avoidance
3. Suggestion chips should wrap properly on small screens
4. Reduce font sizes on very small screens (<360px)

### 8.2 Data Table Responsiveness

**Files**: `DataTable.tsx` and all table usage

**Changes**:
1. Implement horizontal scroll with sticky first column for wide tables
2. Consider card layout for very small screens
3. Add column visibility toggles for dense data

### 8.3 Touch Target Audit

**Files**: Audit across all interactive elements

**Changes**:
1. Ensure all interactive elements have minimum 44×44px touch targets (WCAG 2.5.8)
2. Add adequate spacing between touch targets (minimum 8px)
3. Review the pipeline Kanban cards for mobile drag behavior

---

## 9. Phase 6 — Accessibility & Performance

### 9.1 Accessibility Audit

**Changes**:
1. **Color contrast**: Verify all text/background combinations meet WCAG AA (4.5:1 for normal text, 3:1 for large)
2. **Focus indicators**: Ensure `:focus-visible` rings are consistent and visible (current pattern is good, audit for gaps)
3. **Keyboard navigation**: Tab through all interactive flows — login → workspace → estimator → admin
4. **Screen reader**: Add `aria-live` regions for dynamic content (estimator streaming, toast notifications)
5. **Reduced motion**: Audit all Framer Motion components for `useReducedMotion`

### 9.2 Performance Optimization

**Changes**:
1. **Bundle analysis**: Run `@next/bundle-analyzer` to identify large dependencies
2. **Image optimization**: Ensure all images use `next/image` with proper sizes and lazy loading
3. **Component splitting**: Consider splitting the estimator page into smaller chunks
4. **CSS purging**: Verify Tailwind production build removes unused classes
5. **React.memo audit**: Add memoization to expensive list renders (estimates list, pipeline cards)

### 9.3 Legacy Code Cleanup

**Changes**:
1. Audit usage of legacy CSS classes (`glass`, `card`, `btn-primary`, `btn-secondary`, `input`, `badge`)
2. Replace with v5.1 shell equivalents where found
3. Remove legacy aliases from `globals.css` once all consumers are migrated
4. Remove legacy motion tokens (`--duration-fast-legacy`, etc.)

---

## 10. Measurement & Verification

### Visual Regression
- Use Playwright screenshot tests for key pages: login, workspace, estimator, estimates list
- Capture both light and dark mode
- Run on CI for every PR

### Accessibility
- Run `@axe-core/playwright` on all key pages
- Target: 0 critical/serious violations
- Verify keyboard navigation completes all primary workflows

### Performance
- Lighthouse scores target: Performance ≥ 90, Accessibility ≥ 95
- First Load JS budgets (from existing `scripts/check-bundle-budget.mjs`):
  - Pages under 150KB: 90+ routes
  - Pages 150-250KB: estimator, admin
- No page should exceed 300KB First Load JS

### Manual QA Checklist
- [ ] Auth flow (login → forgot password → reset) in light and dark mode
- [ ] Workspace home with KPIs, recent jobs, activity
- [ ] Full estimator flow (quick quote → line items → send proposal)
- [ ] Pipeline board (create, drag, update projects)
- [ ] Estimates list (filter, search, sort, paginate)
- [ ] Admin tabs (all 9 tabs load and function)
- [ ] Settings pages (profile, org, memory)
- [ ] All empty states display correctly
- [ ] All error states with retry work
- [ ] Mobile: all pages render at 375px, 414px, 768px breakpoints
- [ ] Dark mode toggle works on every page
- [ ] Keyboard navigation (Tab, Enter, Escape, Arrow keys)

---

## Appendix: File Change Summary

| Phase | Files Changed | Estimated Effort |
|---|---|---|
| Phase 1 | 8-10 files | 4-6 hours |
| Phase 2 | 3-4 files | 2-3 hours |
| Phase 3 | 10-15 files | 4-6 hours |
| Phase 4 | 10-12 new `loading.tsx` + 3-4 existing | 3-5 hours |
| Phase 5 | 5-8 files | 3-4 hours |
| Phase 6 | 5-10 files | 3-4 hours |
| **Total** | **~40-55 files** | **19-28 hours** |

## 11. Implementation Log

This section tracks the UI reorganization and cleanup work as it is completed.

### 2026-06-11 — Phase 5 / Forms & Accessibility complete

Form standardization and accessibility improvements were implemented as part of the broader UI reorganization (`plan-ui-reorganization-cleanup.md`).

**Completed**
- Migrated `settings/ProfilePage.tsx` to `react-hook-form` + `zod` shared schemas (profile + password forms).
- Migrated `settings/OrganizationPage.tsx` to `react-hook-form` + `zod` (organization form + invite modal).
- Migrated `admin/UsersPage.tsx` invite modal to shared zod schema.
- Migrated `admin/FeatureFlagsTab.tsx` new-flag form to shared zod schema.
- Added `web/src/lib/forms/schemas.ts` with reusable schemas and `normalizeOrganizationValues` helper.
- Added `web/src/lib/forms/schemas.test.ts` (17 tests).
- Added `GlobalAnnouncer` + `useAnnouncer` hook in `ClientLayout` for screen-reader status announcements.
- Added `prefers-reduced-motion` guard to `Modal.tsx` animations.
- Verified existing modal focus trap, focus restoration, Escape handling, and skip-to-main link.

**Verification**
- `npm run lint` — clean
- `npx tsc --noEmit` — clean
- `npm run test` — 33 files, 178 tests passed
- `npm run build:prod` + `npm run perf:budget` — all routes within budget
- `npm run analyze` — bundle analyzer reports generated in `.next/analyze/`

### 2026-06-11 — Phase 6 / Performance close-out

- Refreshed `docs/PERFORMANCE_BUDGET.md` to the 5.7.0 / Phase 5 baseline.
- Ran `@next/bundle-analyzer`; no unexpected dependency bloat from `react-hook-form` / `zod`.
- Added form conventions to `AGENTS.md`.

### Remaining deferred work

- Full `@axe-core/playwright` accessibility scan across all key pages.
- Playwright visual regression pass for light/dark mode screenshots.
- Manual keyboard navigation QA through login → workspace → estimator → admin.
- Remaining trivial one-field forms can be migrated to `react-hook-form` opportunistically.

### 2026-06-11 — Phase 6 / Performance, Docs & Final Verification complete

**Completed**
- Refreshed `docs/PERFORMANCE_BUDGET.md` to the 5.7.0 / Phase 5 baseline.
- Ran `npm run analyze`; bundle analyzer reports saved to `.next/analyze/`.
- Updated `AGENTS.md` with form conventions.
- Updated `plan-ui-reorganization-cleanup.md` success criteria.

**Final verification results**
| Check | Result |
|---|---|
| `npm run lint` | ✅ clean |
| `npx tsc --noEmit` | ✅ clean |
| `npm run test` | ✅ 33 files, 178 tests passed |
| `npm run build:prod` | ✅ green |
| `npm run perf:budget` | ✅ all routes within budget |
| `npm run test:e2e` | ✅ 19 passed, 3 skipped |

**Outstanding items (not blockers)**
- Run full `@axe-core/playwright` accessibility scan.
- Run full `@axe-core/playwright` accessibility scan.
- Complete Playwright visual regression pass for light/dark mode.
