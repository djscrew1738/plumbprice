# Changelog

All notable changes to PlumbPrice are documented here.

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
