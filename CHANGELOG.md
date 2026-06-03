# Changelog

All notable changes to PlumbPrice are documented here.

## 3.0.0 — AI & Pricing Engine Overhaul (2026-05-17)

### Structured LLM Outputs
- New `llm_structured.py` service replaces fragile `json_object` + `json.loads()` with Pydantic-structured generation via OpenAI `parse()`.
- `ClassifyResult` model includes `reasoning` field for transparent chain-of-thought.
- 3 retries with exponential backoff + fallback to keyword classifier on total failure.

### Tool-Calling Agent v3
- New `agent_v3.py` orchestrator with parallel tool execution:
  `search_materials`, `get_labor_template`, `lookup_permit_cost`, `check_price_history`, `get_market_adjustments`.
- Clarification mode when confidence < 0.8 — asks follow-up questions instead of guessing.
- Full agent trace persistence to `agent_tool_calls` table for audit/debug.

### Dynamic Market Pricing Engine
- New `market_pricing.py` engine applies transparent factor adjustments to estimates.
- Admin CRUD at `/admin/market-pricing` with impact preview on sample estimates.
- Redis caching layer (5-minute TTL) for active adjustments to reduce DB load.
- Cache invalidation on create/update/delete.

### Blueprint Vision v3
- `vision_v3.py` with fixture detection (bounding boxes), room detection (area sqft), and pipe run estimation (linear ft).
- Celery worker updated to persist all three result sets: `BlueprintDetection`, `BlueprintRoom`, `BlueprintPipeRun`.
- New `/api/v3/blueprints/quick-analyze` endpoint for instant image analysis from chat.

### API v3 Router Suite
- `/api/v3/chat` — SSE streaming with `reasoning`, `tool_call`, `tool_result`, `pricing`, `clarification` events.
- `/api/v3/estimates` — CRUD with market adjustment awareness.
- `/api/v3/blueprints` — Upload + takeoff with rooms & pipe runs.
- `/api/v3/market-pricing` — Admin CRUD + preview.
- `/api/v3/suppliers` — Health dashboard + HMAC-verified webhook receiver.
- `/api/v3/agent-trace` — Debug/audit inspector.
- v1 routes now emit `Deprecation`, `Sunset`, and `Link` headers (sunset 2026-09-01).

### Frontend v3 Estimator
- `EstimatorPageV3` is now the default at `/estimator`.
- SSE streaming with `ReasoningBubble`, `ToolCallBubble`, `EstimateBreakdownV3`.
- Blueprint image upload in chat — attaches image, runs quick vision analysis, prepends summary to message.
- `MarketAdjustmentBadge` shows each applied factor with rationale.
- `ClarificationModal` opens when confidence is below threshold.

### Admin v3 Pages
- `/admin/market-pricing` — CRUD + preview.
- `/admin/agent-traces` — Search by estimate ID, view classification reasoning + tool calls.
- `/admin/supplier-health` — Supplier status, product counts, webhook delivery stats.

### Infrastructure
- Database migration `v3p0p0_ai_overhaul_2026_05.py` adds 5 new tables + v3 columns.
- Version bumped: `2.5.1` → `3.0.0`.

## Unreleased — UI overhaul

Goal: reduce visual clunkiness, get estimators to action faster, tighten
density without losing branding (burnt-orange palette, Plus Jakarta Sans).

### Foundations
- New design tokens added to `globals.css` (additive, non-breaking):
  `--surface-1/2/3`, `--border-subtle/strong`, `--ring-focus`,
  `--radius-xs/sm/md/lg/xl/2xl`, `--shadow-sm/md/lg/xl`, density vars
  `--space-page-x/y/section/card`, sidebar rail width `--sidebar-rail`
  (64px) + dynamic `--sidebar-current` for hover-expand without reflow.
- Header height slimmed from 68 → 64px (56px on `<= sm`).
- New layout shell primitives under `web/src/components/layout/shell/`:
  `PageShell`, `PageHeader`, `Section`, `Stack`, `Inline`, `Grid`.
- New hooks: `useReducedMotion`, `useBreakpoint` (+ `useMinBreakpoint`),
  `useSidebarPinned` (persisted via `localStorage["pp_sidebar_pinned"]`).
- Added Radix primitives + `cmdk` + `react-hook-form` + `zod` to support
  upcoming a11y-hardened menus, command palette, and form layer. Existing
  primitives are unchanged.

### Navigation chrome
- **Sidebar**: rebuilt as a 64px icon rail that hover/focus-expands to
  248px, with a pin toggle (persists across sessions). Collapsed nav rows
  show Radix tooltips on the right for keyboard a11y. Hover-expand
  overlays content with elevation `--shadow-lg` instead of pushing it.
  Recent jobs list only renders when expanded.
- **Header**: single-line truncating breadcrumb on `sm+`, just the page
  title on mobile. DFW pill moved to `md+` only. Tighter horizontal
  padding and 40px tap targets on the menu/avatar buttons.
- **MobileNav**: now respects `prefers-reduced-motion` (no slide
  animation on the active-tab indicator). Icons bumped to 20px for
  better legibility.

### Home redesign (action-first launcher)
- Replaced marketing-style hero with **HomeHero**: two large primary
  action tiles (`New estimate`, `Upload blueprint`) plus an optional
  Resume tile when an open chat session exists.
- Replaced the icon-heavy 5-card stat grid with **KpiStrip**: compact,
  icon-free, horizontally scrollable on mobile, with optional links and
  warning/success tones.
- New **ActivityPanel**: side-by-side Recent jobs / Recent sessions on
  `lg+`, tabbed (Radix Tabs) on smaller viewports.
- New **InsightsPanel**: collapsible chart panel + expired-estimate
  warning banner. Chart is lazy-loaded via `next/dynamic` to keep the
  Home initial bundle lean.
- Sub-components extracted to `web/src/components/workspace/home/` for
  focused testing and bundle-splitting.
- Updated `LauncherHome.test.tsx` to assert the new copy / link names
  while preserving the original href contracts.

### Utilities
- `@/lib/utils` now exports `formatCurrency`, `formatCurrencyDecimal`,
  `formatRelativeTime`, `downloadBlob`, and `getConfidenceColor`
  alongside the existing `cn` helper.

### Components
- `Button` gained an `xs` size (px-2.5 / 11px text / rounded-lg) for
  tight chip rows and KPI tiles; existing sizes unchanged.

### Stubs (unblocking pre-existing branch breakage)
Minimal implementations added so the redesign isn't blocked by missing
modules from the in-progress `feat/estimator-mutations-proposals-split`
branch: `@/lib/branding`, `@/lib/notifications`, `@/lib/useOnlineStatus`,
`@/lib/hooks/useWebSocket`, `@/lib/hooks/useOutbox`,
`@/lib/hooks/useFeatureFlags`. Each stub matches the inferred call-site
shape; replace with the real implementations as that work lands.

### Verification
- `npm run build`: green. Home First Load JS = **201 kB** (under the
  210 kB budget; shared baseline still 102 kB).
- `npx vitest run`: 47/47 tests pass, including the updated
  `LauncherHome.test.tsx`.

### Follow-ups (intentionally deferred)
- Adopting `PageShell`/`PageHeader` inside the pipeline / estimates /
  estimator page roots — the existing `PageIntro` is functionally
  equivalent and a swap would be churn without visible gain. Migrate
  opportunistically when those pages get other work.
- Radix-backed `Card`/`Dialog`/`Popover`/`Tooltip`/`Tabs`/`DropdownMenu`
  wrappers, `cmdk` Command Palette, RHF+zod form layer. Dependencies are
  already installed.
- Multi-viewport visual QA pass at 375 / 768 / 1280 / 1920 in light +
  dark.

## 2.5.1 — Reliability + Quality + Speed

### Reliability (already in tree, hardened/verified)
- FastAPI request-logging middleware emits structured JSON access logs with
  request_id, method, path, status, latency_ms, user_id, org_id (skip /health).
- SQLAlchemy slow-query event listener warns at >200 ms with truncated
  statement summary.
- `/api/v1/health/worker` reports Celery broker reachability + per-worker
  active task counts and concurrency.

### Frontend perf
- `MoreSheet` (mobile-only "More" drawer) now lazy-loaded via `next/dynamic`
  with `ssr:false`, removing it from the initial layout chunk.
- `ConfidenceBadge` wrapped in `React.memo` to skip re-renders when score
  stays stable in long estimate breakdowns.
- New `docs/PERFORMANCE_BUDGET.md` records the per-route First Load JS
  baseline so future regressions are visible at PR time.

### Test debt
- Fixed three pre-existing test failures so CI is a useful gate again:
  - `LauncherHome.test.tsx` updated to expect new `/estimates/[id]` hrefs.
  - `Header.test.tsx` and `EstimatesListPage.test.tsx` now provide a
    `QueryClientProvider` and mock `flagsApi`/`notificationsApi`/`estimatesApi`
    consistently with the components' current TanStack Query usage.
- All 48 web tests pass.

### Versioning
- `web/package.json` → `2.5.1` (was `0.1.0`).
- `api/app/config.py` `version` → `2.5.1`.
- `api/app/services/external/__init__.py` docstring bumped to 2.5.1.

## 2.1.1 — UI polish + perf

- React Query consistency, ErrorState patterns, dynamic imports for
  ConfirmDialog, memoization across UI primitives, Cloudflare HTML cache rules
  shipped at 1-day TTL with deploy-time purge.
