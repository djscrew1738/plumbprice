# Changelog

All notable changes to PlumbPrice are documented here.

## 5.8.0 — Pricing Engine Expansion (2026-06-09)

### Expanded Catalog (300+ new SKUs)
- **7 new categories**: commercial_fixture, smart_plumbing, medical_healthcare, restaurant_kitchen, industrial, outdoor_irrigation, piping_fittings
- **182 new canonical items** seeded across 3 DFW suppliers (Ferguson, Moore Supply, Apex)
- **59 new labor templates** covering commercial, smart plumbing, medical, restaurant, industrial, and outdoor work
- **Schema additions**: `in_stock`, `lead_time`, `manufacturer`, `msrp`, `category`, `sub_category`, `tags` on `supplier_products`; `tags`, `difficulty_rating`, `required_certifications` on `labor_templates`; new `material_categories` taxonomy table

### Bulk CSV Import
- **Admin bulk import** for supplier products and labor templates with drag-drop CSV upload
- **Dry-run mode** previews all changes before committing to the database
- **Row-level validation** with clear error messages and row numbers
- **Downloadable templates** for both product and labor imports
- **Endpoints**: `POST /admin/pricing/bulk-import/products`, `POST /admin/pricing/bulk-import/labor`

### Price Feed Adapters
- **Generic `PriceFeedAdapter` framework** with central registry for pluggable external feeds
- **Ferguson adapter** — wraps existing OAuth2 API scraper with simulation fallback
- **Kohler scraper** — MSRP scraping from kohler.com with 60% wholesale estimate
- **Moen scraper** — MSRP scraping from moen.com with 60% wholesale estimate
- **AO Smith scraper** — wholesale price scraping from aosmithatlowes.com
- **Hourly sync task** `worker.tasks.price_feed_sync` runs all adapters and updates the database
- **Feed health dashboard** `GET /admin/pricing/feeds/health` shows real-time adapter status

### Admin UI
- **Catalog Browser** tab — searchable, filterable SKU catalog with inventory badges, category filters, and supplier filters
- **Feed Status** tab — cards per feed showing health (green/yellow/red), last sync, items synced, errors
- **Bulk Import** tab — drag-drop CSV upload with dry-run toggle and validation preview

## 5.7.0 — Mobile Phone UI/UX Improvements (2026-06-09)

### v3 Estimator Mobile Rescue
- **Keyboard avoidance** — Ported `visualViewport` tracking from v2 to v3 so the soft keyboard no longer covers the input textarea on iOS/Android.
- **Auto-scroll** — New messages and streaming responses now automatically scroll into view.
- **Bottom nav clearance** — Input area gets safe-area-aware bottom padding so the send button is never hidden by the mobile nav or iOS home indicator.
- **Copy button visibility** — Copy action is now always visible on touch devices (was hover-only, making it invisible on phones).
- **Suggestion chip tap targets** — Chips now wrap properly and meet 44×44px minimum touch target size.
- **Image preview lightbox** — Tapping the 48×48 blueprint preview opens a full-size modal with Remove/Send actions.

### Mobile Data Presentation
- **LineItemsTable** — Removed CSS override that forced the desktop table on mobile; the existing `DataTable` mobile card view now renders correctly.
- **EstimateEditor** — Added a mobile-first card layout (`lg:hidden`) with stacked label/input pairs for each line item. Desktop table unchanged.
- **PublicQuotePage** — Line items now render as cards on narrow viewports (`sm:hidden`) while keeping the table for desktop. Totals grid adapts to 2 columns on mobile.

### Native Mobile Feel
- **Haptic feedback** wired across the app using the existing `lib/haptics.ts` utility:
  - `MobileNav` tab presses, `MoreSheet` item selection, send/stop buttons, copy actions, estimate card actions, field voice recording, field quick-action tiles.
- **`usePullToRefresh` hook** — New reusable hook with touch-event tracking, spring-release animation, and haptic feedback on trigger. Ready to be wired into lists.

### Field Route Polish
- **Field voice** — Haptic feedback on mic press (tap), recording start (selection), recording stop (warning), and estimate generation (success/error).
- **Field home** — Haptic feedback on quick-action tile presses.

### Accessibility
- Touch target audit on all modified components — every interactive element meets or exceeds 44×44px.
- Fixed `jsx-a11y/label-has-associated-control` errors in `EstimateEditor` mobile cards.
- Removed `aria-hidden="true"` from `StatusDropdown` wrapper in `EstimatesListPage` — the status changer is now visible to screen readers.

### Polish & Bug Fixes
- **Code quality** — Consolidated duplicate `lucide-react` imports; extracted `buildMessage()` helper to eliminate 3× duplicated send logic in `EstimatorPageV3`.
- **`usePullToRefresh` hook** — Refactored to use refs for mutable callback state, eliminating constant DOM listener attach/detach cycles. Added multi-touch safety via `touch.identifier` tracking.
- **Field voice race condition** — Moved `MediaRecorder.onstop` assignment before calling `.stop()` to prevent missing the stop event.
- **Field voice stuck recording** — Added `onPointerCancel` and `onPointerLeave` handlers so recording stops if the user scrolls away or the OS cancels the touch.
- **EstimateEditor key collision** — Replaced module-level `_keySeq` singleton with a `useRef` inside the component so multiple editors and HMR no longer share/collide keys.
- **CSV export memory leak** — Added `URL.revokeObjectURL()` after triggering the estimates CSV download in `EstimatesListPage`.
- **StatusDropdown click propagation** — Restructured to stop propagation on individual interactive elements instead of a wrapper div, eliminating an `aria-hidden` anti-pattern.

---

## 5.2.0 — Subtle Animation System (2026-06-07)

### UI Motion
- Centralized animation primitives in `src/components/ui/Motion.tsx`: `FadeIn`, `BlurFade`,
  `SlideUp`, `ScaleIn`, `Reveal`, `Pressable`, `CountUp`, `StaggerContainer`, `StaggerItem`,
  `SlideIn`, `SmoothPresence`, `Pulse`, `HeightAuto`, `Shimmer`, plus `MOTION` constants.
- Every primitive respects `prefers-reduced-motion` via `useReducedMotion()`; no motion is
  essential for comprehension.
- Interactive component polish:
  - `Button` — spring `whileTap` feedback and loading cross-fade.
  - `Tabs` — animated active indicator via `layoutId` spring.
  - `Select` — dropdown enter/exit with `AnimatePresence`.
  - `Toast` — standardized slide/fade spring transitions.
  - `StatCard` — hover lift and `CountUp` value animation.
- Page choreography:
  - Public home (`/`) — staggered badge, headline, CTA, and value-prop cards.
  - Launcher home (`/`) — `PageShell` fade, hero/KPI/activity/insights reveal stagger,
    `CountUp` KPI strip, smooth height on insights chart.
- Workspace polish:
  - `WorkspaceArtifactCard` — mount fade + hover lift.
  - `WorkspaceEmptyState` — icon/text staggered reveal + suggestion hover feedback.

### Utilities
- `parseCurrencyValue()` in `src/lib/utils.ts` parses formatted currency strings back to numbers
  for `CountUp` animations.

### Performance
- No new animation dependencies; reuses existing Framer Motion `^12.37.0`.
- All routes remain within First Load JS budgets (`docs/PERFORMANCE_BUDGET.md` refreshed with
  v5.2.0 baseline). Largest increase is +3 kB on `/`, `/settings`, and `/suppliers`.

## 4.1.0 — AI Intelligence Overhaul + Mobile PWA (2026-06-06)

### Live Supplier Pricing Intelligence
- **Ferguson OAuth2**: `ferguson.py` supports OAuth2 client-credentials flow; token cached in Redis (15-min TTL). Falls back to legacy API key.
- **Price change alerts**: `SupplierPriceAlert` records created automatically when price delta > ±10% after supplier refresh. Admin receives structured alert.
- **Price forecast model**: Weekly Celery beat task (`compute_price_trends`) runs linear regression on 90-day price history; `price_trend` label (rising / stable / falling) surfaced on line items.
- New env vars: `FERGUSON_CLIENT_ID`, `FERGUSON_CLIENT_SECRET`.

### Variance Tracking & Pricing Correction Loop
- **Actual cost capture**: `EstimateOutcome` extended with `actual_materials_cost`, `actual_labor_hours`, `actual_labor_cost`, `actual_total`, `variance_pct`, `closed_at`, `closed_by_user_id`.
- **Close Job API**: `PATCH /api/v1/outcomes/{estimate_id}/close` with `ActualCostInput` schema.
- **Variance analytics dashboard**: New admin page `/admin/variance` — cost variance by task code with bar visualization and systematic-bias indicators.
- **Pricing correction recommendations**: `pricing_corrections.py` service generates advisory `PricingRecommendation` records (min 5 samples, ±5% threshold). Never auto-applies — requires admin approval.
- **Approve/reject API**: `POST /api/v3/analytics/variance/recommendations/{id}/approve|reject` with audit log.

### LLM Fine-Tuning Pipeline
- **Training data extraction**: `finetune_data.py` extracts JSONL pairs from won estimates (confidence ≥ 0.85, msg > 15 chars, ≥1 line item).
- **Fine-tune orchestration**: `worker/tasks/finetune.py` on dedicated `ml` Celery queue — submits OpenAI fine-tuning job, polls to completion, stores model ID in `ml_models` table.
- **A/B shadow testing**: `model_ab.py` routes 10% of classify calls to shadow model silently; promotes when match rate > baseline + 5pp with ≥100 calls.
- **ML Model Registry admin page**: `/admin/models` — lists model versions with shadow metrics, promote/retire actions.
- New env vars: `ML_FINETUNE_ENABLED` (default false), `ML_FINETUNE_MIN_SAMPLES`, `ML_SHADOW_TRAFFIC_PCT`.

### Enhanced Photo-to-Estimate
- **GPT-4V integration**: `vision_v3.py` uses `gpt-4o` with base64 `image_url` format when `VISION_PROVIDER=openai`; Ollama is retained as fallback.
- **Multi-photo sessions**: `PhotoSession` model and `/api/v3/photos/sessions/*` API — create session, add photos, finalize → triggers `analyze_photo_session` worker task.
- **Confidence review flags**: Detections < 0.6 confidence set `needs_review=true`; blueprint review UI highlights these.
- **Pipe run routing**: Pipe runs now carry `from_fixture`, `to_fixture`, `material_type`, `routing_json` for accurate canonical item mapping.

### Advanced Blueprint Takeoff
- **Scale calibration**: `scale_calibration.py` wired into pipeline; `BlueprintPage.scale_ratio` now persisted; pipe run footage = pixel distance × scale_ratio.
- **Structured routing JSON**: `BlueprintPipeRun.routing_json` stores full path routing.

### Mobile PWA for Field Techs
- **PWA manifest**: `manifest.json` with burnt-orange theme, standalone display, `start_url: /field`.
- **Service worker v4.1.0**: Pre-caches `/field`, `/field/photo`, `/field/voice`; background sync handler for outbox; push notification handler.
- **Field tech role**: New `field_tech` role with restricted permissions; `get_current_field_tech()` auth guard.
- **Field mobile UI** (touch-optimized, 44px tap targets):
  - `/field` — home with quick-action tiles, online/offline indicator, outbox sync badge.
  - `/field/photo` — multi-photo capture → instant estimate session.
  - `/field/voice` — hold-to-talk voice quote with county selector.
  - `/field/jobs` — assigned jobs list with status + totals.
- **GPS county detection**: `GET /api/v3/geo/county?lat=&lng=` — static DFW bounding-box lookup, no external API.
- **Web Push notifications**: `push_service.py` (pywebpush/VAPID); `POST /api/v3/notifications/push/subscribe`; triggers on job assignment, price alerts, estimate approval.
- New env vars: `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBSCRIBER_EMAIL`.

### Architecture & Infrastructure
- **ML worker**: New `worker-ml` Celery service (`concurrency=1`, `queues=ml`) for GPU-bound tasks. Default worker now explicitly runs `--queues=default`.
- **HNSW index**: Migration adds `document_chunks_embedding_hnsw` index (m=16, ef_construction=64) for O(log n) pgvector similarity search.
- **Prometheus metrics**: `prometheus-fastapi-instrumentator` wired at `/metrics` (graceful no-op if not installed).
- **Structured log fields**: `model_id`, `model_version`, `llm_latency_ms` added to agent log events.
- **Architecture Decision Records**: `docs/adr/ADR-001-finetune-pipeline.md`, `docs/adr/ADR-002-pwa-offline.md`.
- New DB tables: `supplier_price_alerts`, `pricing_recommendations`, `pricing_adjustments`, `ml_models`, `photo_sessions`, `push_subscriptions`.
- New API routes: `/api/v3/analytics/variance/*`, `/api/v3/ml/models/*`, `/api/v3/geo/*`, `/api/v3/notifications/push/*`, `/api/v3/photos/sessions/*`.
- Test suite: **1506 passing** (18 new v4.1 tests covering geo, pricing corrections, model A/B, price forecast).

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
