# Performance Budget

Captured at the **4.1.0 release** (Next.js 15.5.6 production build, 2026-06-06).
Use this as the reference point for future regression checks. Values are reported by `next build` as **First Load JS** per route, which already accounts for the shared chunks.

## Shared baseline

| Bundle                                      | Size    |
|---------------------------------------------|---------|
| `chunks/1255-*.js` (vendor)                 | 45.5 kB |
| `chunks/4bd1b696-*.js` (React/runtime)      | 54.2 kB |
| Other shared chunks                         |  2.3 kB |
| **Total shared First Load JS**              | **102 kB** |

Middleware: 32.5 kB.

## Per-route First Load JS (v4.1.0 baseline budget)

| Route                              | Page Size | First Load JS | Budget |
|------------------------------------|-----------|---------------|--------|
| `/`                                | 16.9 kB   | 200 kB        | ≤ 220 kB |
| `/accept-invite`                   |  4.1 kB   | 180 kB        | ≤ 200 kB |
| `/admin`                           | 16.7 kB   | 255 kB        | ≤ 280 kB |
| `/admin/agent-traces`              |  3.5 kB   | 126 kB        | ≤ 145 kB |
| `/admin/jobs`                      |  6.9 kB   | 189 kB        | ≤ 210 kB |
| `/admin/market-pricing`            |  4.4 kB   | 140 kB        | ≤ 160 kB |
| `/admin/models`                    |  7.1 kB   | 145 kB        | ≤ 165 kB |
| `/admin/supplier-health`           |  3.8 kB   | 134 kB        | ≤ 155 kB |
| `/admin/users`                     |  1.0 kB   | 239 kB        | ≤ 260 kB |
| `/admin/variance`                  |  6.7 kB   | 145 kB        | ≤ 165 kB |
| `/analytics`                       |  6.9 kB   | 231 kB        | ≤ 250 kB |
| `/blueprints`                      |  9.4 kB   | 231 kB        | ≤ 250 kB |
| `/blueprints/[id]/review`          |  4.5 kB   | 130 kB        | ≤ 150 kB |
| `/capture`                         |  5.1 kB   | 131 kB        | ≤ 150 kB |
| `/changelog`                       |  0.2 kB   | 106 kB        | ≤ 120 kB |
| `/documents`                       |  9.8 kB   | 234 kB        | ≤ 255 kB |
| `/estimates`                       |  9.7 kB   | 237 kB        | ≤ 260 kB |
| `/estimates/[id]`                  | 15.7 kB   | 252 kB        | ≤ 275 kB |
| `/estimator`                       | 11.6 kB   | 181 kB        | ≤ 205 kB |
| `/field`                           |  2.8 kB   | 112 kB        | ≤ 130 kB |
| `/field/jobs`                      |  1.8 kB   | 223 kB        | ≤ 245 kB |
| `/field/photo`                     |  3.5 kB   | 113 kB        | ≤ 130 kB |
| `/field/voice`                     |  3.4 kB   | 136 kB        | ≤ 155 kB |
| `/forgot-password`                 |  3.6 kB   | 179 kB        | ≤ 200 kB |
| `/login`                           |  4.6 kB   | 180 kB        | ≤ 200 kB |
| `/offline`                         |  1.2 kB   | 103 kB        | ≤ 120 kB |
| `/p/[token]`                       |  6.8 kB   | 109 kB        | ≤ 130 kB |
| `/p/[token]/status`                |  2.0 kB   | 104 kB        | ≤ 120 kB |
| `/pipeline`                        | 10.0 kB   | 238 kB        | ≤ 260 kB |
| `/projects/[id]`                   |  5.7 kB   | 192 kB        | ≤ 210 kB |
| `/proposals`                       | 10.7 kB   | 205 kB        | ≤ 225 kB |
| `/quote`                           |  2.4 kB   | 128 kB        | ≤ 145 kB |
| `/reset-password`                  |  4.2 kB   | 180 kB        | ≤ 200 kB |
| `/sessions`                        |  7.4 kB   | 229 kB        | ≤ 250 kB |
| `/settings`                        | 15.7 kB   | 250 kB        | ≤ 275 kB |
| `/suppliers`                       | 10.8 kB   | 232 kB        | ≤ 255 kB |
| `/voice`                           |  2.0 kB   | 127 kB        | ≤ 145 kB |
| `/voice`                           |  2.0 kB   | 127 kB        | ≤ 150 kB |

The "Budget" column is roughly +10% headroom over the current baseline. PRs that
push a route past its budget should justify why or land an offsetting reduction.

## Notable changes from 2.5.1 → 3.0.0

- **`/estimator`**: First Load JS dropped from **234 kB → 186 kB** (−48 kB, −20%).
  Driven by API layer modularization (`src/lib/api.ts` split into domain modules)
  and additional `next/dynamic` lazy-loading.
- **New routes**: `/admin/agent-traces`, `/admin/market-pricing`, `/admin/supplier-health`.
- **`/quote`**: First Load JS increased from **104 kB → 128 kB** (+24 kB). Under
  investigation; likely from shared-chunk redistribution after estimator splitting.

## How to refresh this baseline

```bash
cd web && npm run build
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

## API P95 Latency Targets (v4.1.0)

Targets are measured end-to-end from client to FastAPI response (excluding Ollama / OpenAI roundtrips). Measure with `k6` or `wrk` against `http://localhost:8000`.

| Endpoint                                  | P95 Target | Notes |
|-------------------------------------------|------------|-------|
| `POST /api/v1/chat`                       | ≤ 3 s      | Chat + pricing engine (TTFB for SSE) |
| `POST /api/v3/chat`                       | ≤ 3 s      | Streaming TTFB |
| `GET /api/v1/estimates/{id}`              | ≤ 200 ms   | DB read + line items |
| `POST /api/v1/estimates/service`          | ≤ 500 ms   | Pricing engine sync |
| `POST /api/v3/blueprints/quick-analyze`   | ≤ 10 s     | GPT-4V or Ollama per page |
| `POST /api/v3/photos/sessions/{id}/add`   | ≤ 5 s      | Upload + MinIO write |
| `GET /api/v3/analytics/variance`          | ≤ 300 ms   | DB aggregation |
| `GET /api/v3/ml/models`                   | ≤ 150 ms   | Simple DB read |
| `GET /metrics`                            | ≤ 50 ms    | Prometheus scrape |

### Implemented optimizations (v4.1.0)

- HNSW index on `document_chunks.embedding` — O(log n) ANN for RAG queries (was sequential scan).
- Prometheus `/metrics` via `prometheus-fastapi-instrumentator` for continuous P95 tracking.
- `ML_SHADOW_TRAFFIC_PCT=10` — shadow model classification is async-fire-and-forget; does not block the main request path.

### 4.1.0

- `PhotoAnnotationCanvas` uses native `<canvas>` API (no heavy library) — draw call is O(n detections).
- Field UI pages (`/field/*`) are lightweight (≤ 3.5 kB page size) — no analytics imports.
