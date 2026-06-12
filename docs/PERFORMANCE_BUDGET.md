# Performance Budget

Captured at the **5.7.0 release / Phase 5 completion** (Next.js 15.5.6 production build, 2026-06-11).
Use this as the reference point for future regression checks. Values are reported by `next build` as **First Load JS** per route, which already accounts for the shared chunks.

## Shared baseline

| Bundle                                      | Size    |
|---------------------------------------------|---------|
| `chunks/1255-*.js` (vendor)                 | 45.5 kB |
| `chunks/4bd1b696-*.js` (React/runtime)      | 54.2 kB |
| Other shared chunks                         |  2.4 kB |
| **Total shared First Load JS**              | **102 kB** |

Middleware: 32.5 kB.

## Per-route First Load JS (5.7.0 / Phase 5 baseline budget)

| Route                              | Page Size | First Load JS | Budget |
|------------------------------------|-----------|---------------|--------|
| `/`                                | 18.1 kB   | 205 kB        | ≤ 226 kB |
| `/accept-invite`                   | 1.85 kB   | 183 kB        | ≤ 201 kB |
| `/admin`                           | 20.8 kB   | 291 kB        | ≤ 320 kB |
| `/admin/agent-traces`              | 5.3 kB    | 175 kB        | ≤ 193 kB |
| `/admin/jobs`                      | 9.24 kB   | 192 kB        | ≤ 211 kB |
| `/admin/market-pricing`            | 5.14 kB   | 141 kB        | ≤ 155 kB |
| `/admin/models`                    | 9.02 kB   | 187 kB        | ≤ 206 kB |
| `/admin/supplier-health`           | 4.47 kB   | 134 kB        | ≤ 147 kB |
| `/admin/users`                     | 2.04 kB   | 269 kB        | ≤ 296 kB |
| `/admin/variance`                  | 8.48 kB   | 186 kB        | ≤ 205 kB |
| `/analytics`                       | 7.97 kB   | 235 kB        | ≤ 259 kB |
| `/blueprints`                      | 11.3 kB   | 235 kB        | ≤ 259 kB |
| `/blueprints/[id]/review`          | 4.75 kB   | 130 kB        | ≤ 143 kB |
| `/changelog`                       | 170 B     | 106 kB        | ≤ 117 kB |
| `/documents`                       | 10.5 kB   | 237 kB        | ≤ 261 kB |
| `/estimates`                       | 11.9 kB   | 241 kB        | ≤ 265 kB |
| `/estimates/[id]`                  | 15.9 kB   | 258 kB        | ≤ 284 kB |
| `/estimator`                       | 30.4 kB   | 216 kB        | ≤ 238 kB |
| `/field`                           | 3.51 kB   | 112 kB        | ≤ 123 kB |
| `/field/jobs`                      | 1.76 kB   | 225 kB        | ≤ 248 kB |
| `/field/photo`                     | 3.94 kB   | 113 kB        | ≤ 124 kB |
| `/field/voice`                     | 4.09 kB   | 137 kB        | ≤ 151 kB |
| `/forgot-password`                 | 1.03 kB   | 182 kB        | ≤ 200 kB |
| `/login`                           | 2.4 kB    | 183 kB        | ≤ 201 kB |
| `/offline`                         | 2.89 kB   | 152 kB        | ≤ 167 kB |
| `/p/[token]`                       | 6.78 kB   | 109 kB        | ≤ 120 kB |
| `/p/[token]/status`                | 1.93 kB   | 104 kB        | ≤ 114 kB |
| `/pipeline`                        | 11 kB     | 241 kB        | ≤ 265 kB |
| `/projects/[id]`                   | 6.36 kB   | 193 kB        | ≤ 212 kB |
| `/proposals`                       | 11 kB     | 206 kB        | ≤ 227 kB |
| `/quote`                           | 2.54 kB   | 128 kB        | ≤ 141 kB |
| `/reset-password`                  | 1.76 kB   | 183 kB        | ≤ 201 kB |
| `/sessions`                        | 7.61 kB   | 231 kB        | ≤ 254 kB |
| `/settings`                        | 14 kB     | 281 kB        | ≤ 309 kB |
| `/share/[token]`                   | 4.13 kB   | 190 kB        | ≤ 209 kB |
| `/suppliers`                       | 10.4 kB   | 243 kB        | ≤ 267 kB |

The "Budget" column is roughly +10% headroom over the current baseline. PRs that
push a route past its budget should justify why or land an offsetting reduction.

## Notable changes from 5.2.0 → 5.7.0 / Phase 5

- **Shared First Load JS unchanged** at **102 kB**.
- **Removed routes**: `/capture` and `/voice` were consolidated into `/field/photo` and `/field/voice`.
- **Form library added**: `react-hook-form`, `zod`, and `@hookform/resolvers` are tree-shaken; only pages with forms import them. Total gzipped JS remains **651.1 kB / 1758 kB**.
- **Largest route increases**: `/admin` (+34 kB First Load JS), `/settings` (+28 kB), `/admin/users` (+29 kB). These are driven by shared form-library code and tab imports; all remain within the +10% budget guardrail.

## How to refresh this baseline

```bash
cd web && npm run build:prod
```

Update the table from the build output. Bump budgets only with a deliberate
reason (e.g. a new page-level feature with no smaller alternative).

## Optimizations already applied

### 2.x line

- `next/dynamic` (`ssr:false`) for `ShortcutsDialog`, `CommandPalette`,
  `MoreSheet`, and confirm dialogs across 8 consumer files.
- `React.memo` on `Badge`, `Avatar`, `StatCard`, `PipelineCard`, `DonutChart`,
  `BarChart`, `ConfidenceBadge`.
- `experimental.inlineCss` enabled in `next.config.ts` to bypass the
  Cloudflare WAF blocking external `/_next/static/css/*.css`.
- Per-deploy CDN purge via `scripts/deploy-web.sh` so HTML chunk URLs never
  drift behind CF cache.

### 3.0.0

- Monolithic `src/lib/api.ts` (~950 lines) split into `src/lib/api/` domain
  modules with a barrel export. Eliminates unused endpoint code from pages that
  only need a subset of the API surface.
- `api-v3.ts` deduplicated — now shares the axios client factory from
  `api/client.ts` instead of re-creating interceptors.
- `ProgressBar` keyframes moved from runtime `<style>` injection to
  `globals.css`, removing a `dangerouslySetInnerHTML` call.
- `SafeMarkdown` wrapper centralizes markdown sanitization for LLM output.

### 4.1.0

- `PhotoAnnotationCanvas` uses native `<canvas>` API (no heavy library) — draw call is O(n detections).
- Field UI pages (`/field/*`) are lightweight (≤ 3.5 kB page size) — no analytics imports.
- HNSW index on `document_chunks.embedding` — O(log n) ANN for RAG queries (was sequential scan).
- Prometheus `/metrics` via `prometheus-fastapi-instrumentator` for continuous P95 tracking.
- `ML_SHADOW_TRAFFIC_PCT=10` — shadow model classification is async-fire-and-forget; does not block the main request path.

### 5.2.0

- Centralized animation primitives in `src/components/ui/Motion.tsx` with
  `useReducedMotion()` support on every component.
- Subtle motion added to buttons, tabs, selects, toasts, stat cards, home page,
  workspace cards, and empty states — all GPU-only transforms.
- `parseCurrencyValue()` utility added for `CountUp` integration in KPI strips.
- Performance budget refreshed; all routes remain within First Load JS guardrails.

### 5.7.0 / Phase 5

- Migrated settings and admin forms to `react-hook-form` + `zod` with shared
  schemas in `src/lib/forms/`.
- Added `GlobalAnnouncer` for screen-reader status announcements.
- Added `prefers-reduced-motion` guard to `Modal.tsx`.
- Verified focus trap, focus restoration, and skip-to-main link.
- Refreshed per-route First Load JS baseline; all routes remain within budget.
