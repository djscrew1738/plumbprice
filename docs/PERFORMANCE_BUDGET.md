# Performance Budget

Captured at the 2.5.1 release (Next.js 15.5.6 production build).
Use this as the reference point for future regression checks. Values are reported by `next build` as **First Load JS** per route, which already accounts for the shared chunks.

## Shared baseline

| Bundle                                      | Size    |
|---------------------------------------------|---------|
| `chunks/1255-*.js` (vendor)                 | 45.5 kB |
| `chunks/4bd1b696-*.js` (React/runtime)      | 54.2 kB |
| Other shared chunks                         |  2.1 kB |
| **Total shared First Load JS**              | **102 kB** |

Middleware: 32.5 kB.

## Per-route First Load JS (baseline budget)

| Route                              | Page Size | First Load JS | Budget |
|------------------------------------|-----------|---------------|--------|
| `/`                                |  9.3 kB   | 193 kB        | ≤ 210 kB |
| `/accept-invite`                   |  4.0 kB   | 180 kB        | ≤ 200 kB |
| `/admin`                           | 16.4 kB   | 250 kB        | ≤ 270 kB |
| `/admin/jobs`                      |  6.5 kB   | 189 kB        | ≤ 210 kB |
| `/admin/users`                     |  0.7 kB   | 234 kB        | ≤ 250 kB |
| `/analytics`                       |  6.7 kB   | 232 kB        | ≤ 250 kB |
| `/blueprints`                      |  7.2 kB   | 230 kB        | ≤ 250 kB |
| `/blueprints/[id]/review`          |  3.0 kB   | 129 kB        | ≤ 150 kB |
| `/capture`                         |  4.9 kB   | 131 kB        | ≤ 150 kB |
| `/changelog`                       |  0.2 kB   | 105 kB        | ≤ 120 kB |
| `/documents`                       |  9.5 kB   | 235 kB        | ≤ 250 kB |
| `/estimates`                       |  8.5 kB   | 238 kB        | ≤ 260 kB |
| `/estimates/[id]`                  | 19.2 kB   | 251 kB        | ≤ 270 kB |
| `/estimator`                       | 55.8 kB   | 234 kB        | ≤ 260 kB |
| `/forgot-password`                 |  3.5 kB   | 179 kB        | ≤ 200 kB |
| `/login`                           |  4.5 kB   | 177 kB        | ≤ 200 kB |
| `/offline`                         |  1.2 kB   | 103 kB        | ≤ 120 kB |
| `/p/[token]`                       |  6.6 kB   | 108 kB        | ≤ 130 kB |
| `/p/[token]/status`                |  2.0 kB   | 104 kB        | ≤ 120 kB |
| `/pipeline`                        | 11.7 kB   | 239 kB        | ≤ 260 kB |
| `/projects/[id]`                   |  5.3 kB   | 192 kB        | ≤ 210 kB |
| `/proposals`                       | 12.5 kB   | 204 kB        | ≤ 220 kB |
| `/quote`                           |  2.0 kB   | 104 kB        | ≤ 120 kB |
| `/reset-password`                  |  4.1 kB   | 180 kB        | ≤ 200 kB |
| `/sessions`                        |  6.5 kB   | 230 kB        | ≤ 250 kB |
| `/settings`                        | 15.4 kB   | 245 kB        | ≤ 265 kB |
| `/suppliers`                       | 10.2 kB   | 233 kB        | ≤ 250 kB |
| `/voice`                           |  1.8 kB   | 128 kB        | ≤ 150 kB |

The "Budget" column is roughly +10% headroom over the current baseline. PRs that
push a route past its budget should justify why or land an offsetting reduction.

## How to refresh this baseline

```bash
cd web && npm run build
```

Update the table from the build output. Bump budgets only with a deliberate
reason (e.g. a new page-level feature with no smaller alternative).

## Optimizations already applied (2.x line)

- `next/dynamic` (`ssr:false`) for `ShortcutsDialog`, `CommandPalette`,
  `MoreSheet`, and confirm dialogs across 8 consumer files.
- `React.memo` on `Badge`, `Avatar`, `StatCard`, `PipelineCard`, `DonutChart`,
  `BarChart`, `ConfidenceBadge`.
- `experimental.inlineCss` enabled in `next.config.ts` to bypass the
  Cloudflare WAF blocking external `/_next/static/css/*.css`.
- Per-deploy CDN purge via `scripts/deploy-web.sh` so HTML chunk URLs never
  drift behind CF cache.
