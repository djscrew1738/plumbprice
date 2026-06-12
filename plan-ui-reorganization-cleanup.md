# PlumbPrice AI — Comprehensive UI Reorganization & Cleanup Plan

> **Version**: 1.0  
> **Scope**: `web/` frontend (Next.js 15, React 19, TypeScript, Tailwind CSS, Framer Motion)  
> **Goal**: Transform the current UI from a collection of well-built but inconsistently applied pieces into a cohesive, maintainable, accessible, and performant interface.

---

## 1. Goal & Scope

### Objective
Reorganize and clean up the overall application UI so that all surfaces share one design system, one component vocabulary, one routing/navigation model, and one pattern for forms, loading, error, and empty states — while preserving existing functionality and staying within the documented performance budget.

### In Scope
- Design-system unification (tokens, primitives, legacy class purge).
- Component architecture cleanup (dead-code removal, duplication elimination, giant-file decomposition).
- Routing & navigation consolidation (duplicate surfaces, admin structure, command palette).
- Form standardization and accessibility improvements.
- Loading, empty, and error state completion.
- Responsive/mobile polish and touch-target audit.
- Documentation updates (`UI_ENHANCEMENT_PLAN.md`, `PERFORMANCE_BUDGET.md`, `AGENTS.md`).

### Out of Scope
- Rewriting business logic or pricing algorithms.
- Changing backend APIs or database schema.
- Rebranding (colors, typography, logo) — we will use the existing v5.1 token system.
- New user-facing features (e.g., new dashboards) beyond what is required for cleanup.

---

## 2. Files to Create / Modify

### New files
| File | Purpose |
|------|---------|
| `web/src/components/ui/Card.tsx` | Canonical card primitive to replace ad-hoc `card`, `shell-card`, `glass-card` classes. |
| `web/src/components/ui/FormLayout.tsx` | Shared form wrapper: label alignment, error grouping, submit actions, aria wiring. |
| `web/src/components/ui/FormSection.tsx` | Grouped form fieldset with optional title/description. |
| `web/src/components/ui/EmptyState.tsx` *(exists; expand)* | Unified empty-state illustration + copy + CTA. |
| `web/src/lib/forms/` | Zod schemas for shared validation (email, password, phone, etc.). |
| `web/src/app/loading.tsx` (remaining routes) | Per-route skeleton loaders. |
| `web/src/components/layout/PublicLayout.tsx` | Minimal centered layout for `/p/*`, `/quote`, auth pages to replace duplicated centering styles. |
| `web/src/components/admin/AdminShell.tsx` | Single admin wrapper to unify tabbed `/admin` and standalone `/admin/*` routes. |
| `web/src/components/estimates/EstimatesFilters.tsx` | Extract filters from `EstimatesListPage`. |
| `web/src/components/estimates/EstimatesTable.tsx` | Extract desktop table from `EstimatesListPage`. |
| `web/src/components/estimates/EstimatesMobileList.tsx` | Extract mobile cards from `EstimatesListPage`. |
| `web/src/components/estimates/EstimatesExport.tsx` | Extract CSV export logic from `EstimatesListPage`. |

### Modify / delete
| File | Action | Reason |
|------|--------|--------|
| `web/src/components/layout/PageIntro.tsx` | **Delete** | No consumers; redundant with `PageHeader`. |
| `web/src/components/estimator/*` (legacy) | **Delete or archive** | `src/app/estimator/page.tsx` uses `EstimatorPageV3`; legacy files are dead weight. |
| `web/src/app/register/page.tsx` | **Delete** | Redirects to `/login`. |
| `web/src/app/capture/page.tsx` | **Merge into** `/field/photo` | Duplicate photo quick-quote flow. |
| `web/src/app/voice/page.tsx` | **Merge into** `/field/voice` | Duplicate voice quick-quote flow. |
| `web/src/components/ui/CommandPalette.tsx` + `web/src/components/estimator-v3/CommandPalette.tsx` | **Merge or namespace** | Both register the same custom event. |
| `web/src/components/ui/ConfirmDialog.tsx` | **Refactor to use `Button`** | Currently reimplements buttons. |
| `web/src/components/ui/Button.tsx` | **Fix shadow token** | Replace hardcoded shadow with `--shadow-elev-*`. |
| `web/src/components/layout/Sidebar.tsx` | **Use CSS vars for widths** | Replace hardcoded `64`/`248` with `--sidebar-rail` / `--sidebar-expanded`. |
| `web/src/components/layout/Header.tsx` | **Use `DropdownMenu` primitive** | Replace custom user-menu dropdown. |
| `web/src/components/layout/MobileNav.tsx` | **Increase indicator, haptic feedback** | 4px active indicator, haptic on press. |
| `web/src/app/globals.css` | **Purge legacy classes** | Remove `.btn-primary`, `.btn-ghost`, `.input`, `.badge-*`, `.card*`, `.glass*`, legacy motion/shadow tokens. |
| `web/src/app/layout.tsx` | **Clean background refs** | Remove redundant legacy background styling. |
| `web/src/components/auth/*.tsx` | **Migrate to tokens + FormLayout** | Eliminate hardcoded colors and inline validation. |
| `web/src/app/error.tsx`, `not-found.tsx` | **Migrate to tokens** | Replace hardcoded dark/blue styling. |
| `web/src/components/settings/*.tsx` | **Adopt FormLayout + zod schemas** | Reduce local state duplication. |
| `web/src/components/admin/AdminPage.tsx` + tabs | **Split and use AdminShell** | Reduce prop drilling and file size. |
| `web/src/components/estimates/EstimatesListPage.tsx` | **Decompose** | Split into filters/table/mobile/export components. |
| `web/src/components/proposals/ProposalsPage.tsx` | **Decompose** | Extract list, filters, create modal. |
| `web/src/components/suppliers/SuppliersPage.tsx` | **Decompose** | Extract table, filters, health panel. |
| `web/src/components/blueprints/BlueprintsPage.tsx` | **Decompose** | Extract upload, list, status cells. |
| `web/src/components/pipeline/ProjectDrawer.tsx` | **Decompose** | Extract sections/tabs into subcomponents. |
| `web/src/middleware.ts` | **Audit public paths** | Add `/accept-invite`, `/share/*`, `/quote`, `/p/*` consistency. |
| `web/src/components/layout/ClientLayout.tsx` | **Page transitions + reduced-motion** | Optional animated page transitions. |
| `docs/UI_ENHANCEMENT_PLAN.md` | **Update** | Mark completed items, add reorganization phases. |
| `docs/PERFORMANCE_BUDGET.md` | **Refresh** | Re-baseline after cleanup. |

---

## 3. Architecture / Key Decisions

### 3.1 One design token family
**Decision**: Standardize on the existing v5.1 custom-property tokens (`--canvas`, `--panel`, `--ink`, `--line`, `--accent`, `--shadow-*`, `--radius-*`) and remove legacy HSL aliases and hardcoded Tailwind colors.

**Trade-off**: Migrating every hardcoded color is mechanical but touches many files. The alternative (keeping dual token families) guarantees continued inconsistency. We will migrate in phases by route/domain to keep PRs reviewable.

### 3.2 Primitive-first UI
**Decision**: Every repeated visual pattern becomes a primitive: `Card`, `FormLayout`, `FormSection`, `EmptyState`, `ErrorState`, `Button`, `Input`, `Badge`. Raw `<button>` and `<input>` usage outside primitives is forbidden.

**Trade-off**: Upfront primitive development slows the first phase, but eliminates duplication and makes future theme changes trivial.

### 3.3 Form library
**Decision**: Introduce `react-hook-form` + `zod` for all non-trivial forms. Trivial one-field forms may remain controlled, but validation logic must live in `src/lib/forms/` schemas.

**Trade-off**: Adds two small dependencies (already common in the ecosystem). The alternative is continuing to reimplement validation per form, which is the current source of bugs and inconsistency.

### 3.4 Page / component boundary
**Decision**: `src/app/**/page.tsx` files remain thin route entry points. All page-level logic and layout moves to `src/components/[domain]/[Page].tsx`. Shared layouts move to `src/components/layout/`.

**Trade-off**: Slightly more files, but aligns with Next.js App Router conventions and makes testing easier.

### 3.5 Duplicate surface consolidation
**Decision**: `/capture` and `/voice` are removed; their URLs redirect to `/field/photo` and `/field/voice`. Admin becomes a single `AdminShell` with tabbed and deep-linkable views.

**Trade-off**: Removes user-facing URLs, but the duplicated flows had diverging implementations; consolidation reduces maintenance and support surface.

### 3.6 Dead-code removal
**Decision**: Delete `PageIntro.tsx`, legacy `estimator/`, and `/register` redirect. If a component has zero importers, it goes.

**Trade-off**: Risk of breaking a dynamic import or undocumented usage. We will verify via `grep` and build before deleting.

---

## 4. Step-by-Step Implementation

### Phase 0 — Audit, Baseline & Tooling (1 week)
1. **Run full build + budget capture**  
   `cd web && npm run build:prod && npm run perf:budget`  
   Record current First Load JS per route.
2. **Generate dead-code report**  
   Use `knip` or a scripted `grep` to find files with zero importers; cross-reference with dynamic imports.
3. **Create a migration tracker**  
   Airtable/Notion/GitHub project board with one card per file/route.
4. **Add lint rules**  
   Extend ESLint to forbid raw `<button>`/`<input>` outside `src/components/ui/` and flag hardcoded Tailwind colors (`bg-blue-*`, `text-zinc-*`, etc.) as warnings.

### Phase 1 — Design System Foundation (2 weeks)
5. **Create `Card.tsx` primitive**  
   Variants: `default`, `outlined`, `ghost`, `interactive`, sizes `sm`/`md`/`lg`. Uses `var(--panel)`, `var(--line)`, `var(--radius-lg)`, `var(--shadow-elev-1)`.
6. **Create `FormLayout.tsx` and `FormSection.tsx`**  
   Includes label, error, hint text, submit/cancel actions, and `aria-invalid`/`aria-describedby` wiring.
7. **Fix `Button.tsx` shadow**  
   Replace hardcoded shadow with `var(--shadow-elev-2)`.
8. **Purge legacy CSS classes from `globals.css`**  
   Remove `.btn-primary`, `.btn-ghost`, `.input`, `.badge-*`, `.card*`, `.glass*`, legacy motion/shadow tokens.
9. **Update `tailwind.config.ts`**  
   Remove any legacy color aliases that are no longer needed; ensure all v5.1 tokens are mapped.
10. **Refresh root `layout.tsx`**  
    Remove redundant background styling; rely on `globals.css` body rules.

### Phase 2 — Remove Dead & Duplicate Code (1 week)
11. **Delete `PageIntro.tsx`**  
    Confirm zero consumers, then remove.
12. **Delete legacy `src/components/estimator/*`**  
    Move to `archive/` if there is any risk, otherwise delete.
13. **Delete `src/app/register/page.tsx`**  
    Add redirect in `next.config.ts` or middleware.
14. **Merge `/capture` → `/field/photo`**  
    Move useful image-preprocessing logic into the field flow; add redirect.
15. **Merge `/voice` → `/field/voice`**  
    Consolidate recorder logic; add redirect.
16. **Resolve command palette conflict**  
    Merge global and estimator command palettes or rename the custom event to `show-estimator-command-palette`.

### Phase 3 — Page & Component Reorganization (3 weeks)
17. **Create `PublicLayout.tsx`**  
    Centered, theme-aware layout for auth and public pages; replace duplicated centering styles.
18. **Migrate auth pages** (`LoginForm`, `ForgotPasswordForm`, `ResetPasswordForm`, `AcceptInviteForm`)  
    Use `PublicLayout`, design tokens, `FormLayout`, and shared zod schemas.
19. **Migrate `error.tsx` and `not-found.tsx`**  
    Use tokens and `Button`; remove hardcoded blue.
20. **Create `AdminShell.tsx`**  
    Unify tabbed `/admin` and standalone `/admin/*` routes; tabs become query-param or path-based navigation.
21. **Split `AdminPage.tsx` tabs**  
    Extract each tab into `src/components/admin/tabs/[Name]Tab.tsx`.
22. **Decompose `EstimatesListPage.tsx`**  
    `EstimatesFilters`, `EstimatesTable`, `EstimatesMobileList`, `EstimatesExport`, `EstimatesSummary`.
23. **Decompose `ProposalsPage.tsx`, `SuppliersPage.tsx`, `BlueprintsPage.tsx`**  
    Apply the same list/filter/detail split pattern.
24. **Decompose `ProjectDrawer.tsx`**  
    Extract tab sections into subcomponents.
25. **Refactor `ConfirmDialog.tsx`**  
    Use `Button` primitive; remove raw buttons.

### Phase 4 — Navigation, Layout & Responsive (2 weeks)
26. **Sidebar token fix**  
    Replace hardcoded widths with CSS variable reads or style props.
27. **Sidebar keyboard navigation**  
    Arrow keys, Home/End, Enter/Space to select.
28. **Header user menu**  
    Replace custom dropdown with `DropdownMenu` primitive.
29. **MobileNav polish**  
    4px active indicator, `layoutId` shared layout, haptic feedback, safe-area review.
30. **Page transitions**  
    Add optional route transition in `ClientLayout.tsx` with `prefers-reduced-motion` guard.
31. **Touch-target audit**  
    Ensure all interactive elements are ≥ 44×44px; fix any 36px icon-only buttons.
32. **Loading states**  
    Add `loading.tsx` to any route still missing one (verify `/field/*`, `/sessions`, public routes).

### Phase 5 — Forms & Accessibility (2 weeks) ✅ Completed
33. **Add `react-hook-form` + `zod`**  
    Dependencies already present; wired into settings and admin forms.
34. **Create shared zod schemas**  
    Added `web/src/lib/forms/schemas.ts` with `profileSchema`, `passwordSchema`, `organizationSchema`, `inviteUserSchema`, `featureFlagSchema`, and `normalizeOrganizationValues` helper.
35. **Migrate `settings/ProfilePage.tsx`**  
    Rewritten with `react-hook-form` + `zodResolver`; profile and password forms use shared schemas.
36. **Migrate `settings/OrganizationPage.tsx`**  
    Rewritten with `react-hook-form` + `zodResolver`; organization form and invite modal use shared schemas.
37. **Migrate remaining admin forms**  
    Migrated `admin/UsersPage.tsx` invite modal and `admin/FeatureFlagsTab.tsx` new-flag form to shared schemas.
38. **Global `aria-live` region**  
    Added `web/src/components/layout/GlobalAnnouncer.tsx` with `useAnnouncer` hook; integrated in `ClientLayout`. Used for profile/organization save confirmations.
39. **Reduce-motion audit**  
    `Modal.tsx` now respects `prefers-reduced-motion` by disabling enter/exit animations. `ClientLayout` page transitions and `Button` already guarded.
40. **Focus management audit**  
    Verified `Modal.tsx` focus trap, initial focus, Escape handling, and focus restoration on close. Skip-to-main link already present in `ClientLayout`.

### Phase 6 — Performance, Docs & Final Verification (1 week) ✅ Completed
41. **Refresh performance budget**  
    Ran `npm run build:prod` and updated `docs/PERFORMANCE_BUDGET.md` to the 5.7.0 / Phase 5 baseline.
42. **Bundle analysis**  
    Ran `npm run analyze`; reports generated in `.next/analyze/`. No unexpected regressions from `react-hook-form` / `zod`.
43. **Update `docs/UI_ENHANCEMENT_PLAN.md`**  
    Added Implementation Log section marking Phase 5 and Phase 6 close-out work.
44. **Update `AGENTS.md`**  
    Added form conventions (primitive-first, `react-hook-form` + zod, schema tests) under Conventions & Patterns.
45. **Final full test run**  
    - `npm run lint` — clean  
    - `npx tsc --noEmit` — clean  
    - `npm run test` — 33 files, 178 tests passed  
    - `npm run test:e2e` — 19 passed, 3 skipped  
    - `npm run perf:budget` — all routes within budget

---

## 5. Testing Strategy

### Unit tests
- Primitive behavior: `Card`, `Button`, `FormLayout`, `Input`, `Badge` render all variants and states.
- Form schemas: each zod schema covers valid input, invalid input, edge cases (empty string, max length, special chars).
- Utility helpers: `cn`, formatters, validation helpers.

### Integration tests
- Route rendering: each refactored page renders without error; loading states appear.
- Navigation: sidebar, mobile nav, command palette, and admin tabs route correctly.
- Form submission: auth, settings, and admin forms submit valid data and display server errors.
- Accessibility: axe-core or `@testing-library/jest-dom` checks for labels, roles, contrast basics.

### End-to-end tests
- Happy path: login → create estimate → view estimate → logout.
- Mobile path: mobile nav, field photo flow, estimator on small viewport.
- Admin path: navigate admin tabs, create/edit markup rule.
- Public path: view shared quote / customer status portal.

### Visual regression
- Run a subset of Playwright screenshots for key routes before and after migration.
- Maintain a temporary "legacy vs. token" screenshot comparison for auth and error pages.

### Performance regression
- Compare First Load JS per route against `docs/PERFORMANCE_BUDGET.md` after each phase.
- `npm run perf:budget` must pass before merging any phase.

---

## 6. Risks & Rollback

### Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Dynamic imports break after deleting "unused" files | Medium | High | Verify with `grep` and `next build` before deleting; archive first. |
| Token migration causes visual regressions in dark/light mode | High | Medium | Migrate route-by-route; screenshot comparisons per route. |
| `react-hook-form` + `zod` increases bundle size | Low | Low | Tree-shakeable; verify with `npm run analyze`. |
| Form refactor introduces validation bugs | Medium | High | Port existing rules exactly into zod schemas; add integration tests. |
| Admin route consolidation changes deep links | Medium | Medium | Add redirects; update nav config. |
| Removing `/capture` and `/voice` breaks bookmarks | Low | Low | Implement 308 redirects in middleware or `next.config.ts`. |
| Large PRs become unreviewable | High | High | One phase per PR; keep each PR under ~20 files when possible. |

### Rollback strategy
- Each phase is its own branch/PR merged independently; rollback is a single revert.
- Archive deleted components for one release before permanent removal.
- Keep `UI_ENHANCEMENT_PLAN.md` updated so any rolled-back phase can be re-attempted.
- Performance budget is a hard gate: if any phase exceeds budgets, it is reverted or offset before merge.

---

## 7. Success Criteria

- [x] `npm run lint` passes with zero warnings.
- [x] `npx tsc --noEmit` passes.
- [x] `npm run test` passes with ≥ current coverage.
- [x] `npm run build:prod` passes and no route exceeds its First Load JS budget.
- [x] No hardcoded Tailwind colors (`bg-blue-*`, `text-zinc-*`, etc.) remain in `src/components/` or `src/app/` (completed in Phases 0–4).
- [x] No raw `<button>` or `<input>` elements outside `src/components/ui/` (completed in Phases 0–4).
- [x] `PageIntro.tsx` and legacy `estimator/` components are removed (completed in Phase 2).
- [x] `/capture` and `/voice` redirect to `/field/photo` and `/field/voice` (completed in Phase 2).
- [x] Settings and admin forms use `react-hook-form` + shared zod schemas (remaining trivial one-field forms to be migrated in Phase 6 if needed).
- [x] `docs/UI_ENHANCEMENT_PLAN.md` and `docs/PERFORMANCE_BUDGET.md` are refreshed.

---

## 8. Suggested Phase Order for Review

1. **Phase 0** (baseline) — required before any code changes.
2. **Phase 1** (design system) — highest leverage; unblocks everything else.
3. **Phase 2** (dead/duplicate code) — reduces surface area quickly.
4. **Phase 3** (page/component reorg) — largest body of work; split into multiple PRs by domain.
5. **Phase 4** (navigation/responsive) — user-facing polish.
6. **Phase 5** (forms/a11y) — quality and compliance.
7. **Phase 6** (perf/docs/final verification) — close-out.
