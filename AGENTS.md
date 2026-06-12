<!-- From: /home/djscrew/Projects/Web-Apps/plumbprice/AGENTS.md -->
# PlumbPrice AI — Agent Guide

This file is the canonical reference for AI coding agents working in this repository. It describes the project structure, build commands, testing strategy, code conventions, and security rules. Read this before making any non-trivial change.

---

## Project Overview

PlumbPrice AI is an autonomous plumbing pricing and estimating platform for DFW-area plumbing contractors. It replaces spreadsheet-based estimating with a chat-driven interface that produces itemized, line-level quotes backed by real supplier pricing data. The system guarantees that every price shown can be traced directly to a supplier SKU and a labor template — the LLM extracts intent and maps it to canonical line items, but all dollar math happens in pure Python with no LLM involvement.

**Current API version:** 5.9.0 (`api/app/config.py`)  
**Current Web version:** 5.7.0 (`web/package.json`)

---

## Technology Stack

| Layer | Technology |
|---|---|
| API | FastAPI (Python 3.13), async-first |
| Database | PostgreSQL 16 + pgvector |
| Cache / Queue broker | Redis 7 |
| Task worker | Celery 5 (Python) — default, high, and ml queues |
| Object storage | MinIO (S3-compatible) |
| Frontend | Next.js 15 (App Router, TypeScript, React 19) |
| Styling | Tailwind CSS 3, Framer Motion, Lucide React |
| AI / LLM | Ollama (local primary, `qwen3:8b` / `hermes3:3b`) with OpenAI / Anthropic / DeepSeek cloud fallback |
| Auth | JWT (access + refresh tokens), passlib+bcrypt |
| Observability | Sentry (optional), OpenTelemetry (optional), Prometheus metrics |
| Proposal PDFs | WeasyPrint |
| Email | Resend (optional) |
| Blueprint analysis | Local vision (`llama3.2-vision`) or OpenAI GPT-4V |

---

## Repository Layout

```
.
├── api/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py         # FastAPI app factory, middleware, router registration, lifespan
│   │   ├── config.py       # Pydantic-settings configuration (Settings class)
│   │   ├── database.py     # SQLAlchemy async engine + session, slow-query logging
│   │   ├── observability.py# Structlog setup, optional Sentry + OTel init
│   │   ├── models/         # SQLAlchemy ORM models (~30 tables)
│   │   ├── routers/        # FastAPI route modules (v1 + v3 subpackages)
│   │   ├── schemas/        # Pydantic request/response models
│   │   ├── services/       # Business logic, external integrations, pricing engine
│   │   └── core/           # Auth, storage, cache, rate limit, exceptions, broker
│   ├── alembic/            # Database migrations (Alembic, ~44 migration files)
│   ├── tests/              # pytest suite (routers/, services/, eval/)
│   ├── scripts/            # Seed script, admin creation
│   ├── requirements.txt    # Runtime + dev dependencies
│   ├── Dockerfile          # Python 3.13 slim
│   └── pyproject.toml      # pytest, coverage config
│
├── web/                    # Next.js frontend
│   ├── src/
│   │   ├── app/            # App Router pages (Next.js 15)
│   │   ├── components/     # React components (by feature: admin, estimator, pipeline, etc.)
│   │   ├── lib/            # API clients, utilities, hooks, offline outbox
│   │   ├── contexts/       # React context providers
│   │   ├── types/          # Shared TypeScript types
│   │   └── test/           # Vitest setup file (stubs matchMedia, IndexedDB, URL.createObjectURL)
│   ├── tests/e2e/          # Playwright end-to-end tests
│   ├── public/             # Static assets, manifest.json
│   ├── scripts/            # Bundle budget checker
│   ├── package.json
│   ├── next.config.ts      # Standalone output, rewrites, headers, Sentry, bundle analyzer
│   ├── vitest.config.ts    # Unit test config (jsdom, v8 coverage)
│   ├── playwright.config.ts# E2E test config (Chromium, baseURL localhost:3200)
│   ├── tailwind.config.ts  # Custom design tokens, semantic colors, animations
│   ├── eslint.config.mjs   # next/core-web-vitals, next/typescript, jsx-a11y, react-hooks
│   └── Dockerfile          # Multi-stage Node 20 build
│
├── worker/                 # Celery background worker
│   ├── tasks/              # Celery task modules
│   │   ├── supplier_refresh.py
│   │   ├── document_processing.py
│   │   ├── blueprint_analysis.py
│   │   ├── privacy.py
│   │   ├── finetune.py
│   │   └── price_forecast.py
│   ├── tests/              # Worker-specific pytest tests
│   ├── worker.py           # Celery app factory + beat schedule
│   ├── requirements.txt
│   └── Dockerfile
│
├── scripts/                # Host-level deployment & utility scripts
├── deploy/                 # Nginx config, runtime.env.example
├── docs/                   # Architecture, API ref, deployment, privacy, perf budget, ADRs
├── docker-compose.yml      # Local dev stack (all services + worker-ml)
├── docker-compose.prod.yml # Production overrides (restart policies, no volume mounts)
├── .env.example            # Required environment variables
├── pytest.ini              # API-only test config
├── pytest-worker.ini       # API + worker combined test config
└── AGENTS.md               # This file
```

---

## Build & Development Commands

### Docker Compose (recommended for local development)

```bash
# Start all services (postgres, redis, minio, api, worker, web, worker-ml)
docker compose up -d

# Run migrations inside the API container
docker compose exec api alembic upgrade head

# Seed the database with demo data (or let auto-seed run on first startup)
docker compose exec api python -m app.scripts.seed

# Tail logs
docker compose logs -f api
docker compose logs -f worker

# Start only backing services (for local dev server usage)
docker compose up -d postgres redis minio
```

### API (local Python)

```bash
cd api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Dev server
uvicorn app.main:app --reload --port 8000

# Migrations (run from repo root or api/)
alembic upgrade head
```

### Worker (local Python)

```bash
# Reuse the API virtualenv or create a separate one
source api/.venv/bin/activate
cd worker
pip install -r requirements.txt

celery -A worker worker --loglevel=info --concurrency=2
```

The worker also defines a `ml` queue for fine-tuning and price-forecast tasks. Run a dedicated ML worker with:

```bash
celery -A worker.worker worker --loglevel=info --concurrency=1 --queues=ml --hostname=worker-ml@%h
```

### Frontend (local Node)

```bash
cd web
npm install

# Dev server (Turbopack)
npm run dev

# Production build (hardcodes https://app.ctlplumbingllc.com as API origin)
npm run build:prod

# Clean rebuild (archives old node_modules/.next, runs npm ci + build)
../scripts/rebuild-web-clean.sh
```

---

## Testing Instructions

### API Tests

```bash
# From repo root — API only
pytest -c pytest.ini

# From api/ directory
pytest
```

- **Config files:** `pytest.ini` (root, API only) and `api/pyproject.toml`
- **Default DB for tests:** In-memory SQLite (`sqlite+aiosqlite:///:memory:`) via test overrides; CI uses PostgreSQL via service container
- **Rate limiting:** Disabled in tests via `limiter.enabled = False`
- **Coverage floor:** **30%** (`fail_under = 30` in `api/pyproject.toml`)
- **Markers:** `asyncio`, `integration`, `unit`
- **Eval harness:** Located in `api/tests/eval/`; skipped by default unless `RUN_EVAL=1` is set
- **Flaky tests:** Some admin/worker and classifier tests are excluded from CI runs (see `.github/workflows/test-coverage.yml`)

### Worker Tests

```bash
# From repo root — API + worker combined
pytest -c pytest-worker.ini
```

- Uses `task_always_eager = True` so Celery tasks run synchronously.
- Redis must be reachable for the broker fixture.

### Frontend Unit Tests

```bash
cd web
npm run test        # Vitest run with coverage
npm run test:watch  # Vitest watch mode
```

- **Config:** `vitest.config.ts`
- **Environment:** `jsdom`
- **Coverage thresholds:** lines 20%, functions 35%, branches 30%, statements 20%
- **Setup file:** `src/test/setup.ts` (extends `@testing-library/jest-dom`, stubs `matchMedia`, `indexedDB`, and `URL.createObjectURL`)

### Frontend E2E Tests

```bash
cd web
npm run test:e2e            # Headless Playwright run
npx playwright test --ui    # Interactive UI mode
```

- **Config:** `playwright.config.ts`
- **Browsers:** Chromium (primary), with global setup for auth state
- **Base URL:** `http://localhost:3200`

### CI Workflows

GitHub Actions in `.github/workflows/`:

| Workflow | Trigger | What it does |
|---|---|---|
| `test-coverage.yml` | push/PR to `main` | API pytest with coverage (PostgreSQL service), frontend vitest + type-check |
| `playwright.yml` | push/PR to `main` | Full E2E suite against running stack |
| `lighthouse.yml` | push/PR to `main` | Lighthouse CI performance audit |
| `qa-bot.yml` | PR events | Automated QA commentary |

---

## Code Style Guidelines

### Python

- **Formatter / Linter:** `ruff check .` and `ruff format .`
- **Type checker:** `mypy app/`
- **Async-first:** All database access uses SQLAlchemy async sessions (`AsyncSession`) and `asyncpg`. Endpoints and services should be `async def` unless there is a clear reason not to.
- **Structured logging:** Use `structlog.get_logger()`; do not use raw `print()` or standard `logging` directly.
- **Import style:** Absolute imports from `app.*` inside `api/`; relative imports inside `worker/`.
- **Config:** All env-driven settings live in `app.config.settings` (Pydantic `BaseSettings`).

### TypeScript / React

- **Linter:** `eslint` with `next/core-web-vitals`, `next/typescript`, `jsx-a11y`, and `react-hooks` (config in `eslint.config.mjs`)
- **Strict mode:** Enabled in `tsconfig.json` (`strict: true`, `noImplicitOverride: true`)
- **Path alias:** `@/*` maps to `src/*`
- **React patterns:** Prefer functional components with hooks. Use `React.memo` for stable UI primitives. Lazy-load heavy components with `next/dynamic` where appropriate.
- **Data fetching:** Use `@tanstack/react-query` for server state; use `axios` for raw HTTP calls.
- **Offline support:** The `/field/*` routes use service worker pre-caching and `outbox.ts` (Dexie/IndexedDB) for offline estimate creation and background sync.

---

## Architecture & Design Principles

### Service Architecture

```
Browser (Next.js 15, port 3000 / 3200)
    │ HTTPS / REST
    ▼
Nginx (reverse proxy, TLS termination by Cloudflare)
    │ /api/*  →  FastAPI (port 8000 / 8200 / 8201)
    │ /       →  Next.js standalone (port 3000 / 3200 / 3201)
    ▼
FastAPI — /api/v1/* (deprecated, maintenance mode) and /api/v3/* (active)
    │ async DB queries           │ enqueue tasks
    ▼                            ▼
PostgreSQL + pgvector      Redis (broker + cache)
                                │
                                ▼
                         Celery Worker — default queue
                         - supplier_refresh (daily beat)
                         - document_processing
                         - blueprint_analysis
                         - privacy.purge_expired_uploads
                                │
                         Celery Worker — ml queue (concurrency=1)
                         - finetune.run_finetune
                         - price_forecast.compute_price_trends (weekly beat)
                                │
                                ▼
                         MinIO (object storage)
                         blueprints / documents / proposals / photos
```

### API Versioning

- **v1:** In maintenance mode. Deprecated with `Deprecation: true` and `Sunset: Sat, 01 Sep 2026 00:00:00 GMT` headers on non-auth responses. New consumers should use v3.
- **v3:** Active development. All new features land here first.

### Key Design Decisions

1. **Deterministic pricing** — The LLM extracts intent and maps to canonical line items. All dollar math is pure Python; the same inputs always produce the same output.
2. **Full traceability** — Every line item carries a `trace_json` blob with supplier, SKU, cost, labor template, and multipliers.
3. **Confidence transparency** — Estimates surface a 0.0–1.0 confidence score and a human-readable label (High / Medium / Low / Estimate-Only).
4. **Async-first API** — SQLAlchemy async sessions + asyncpg for I/O-bound endpoints.
5. **Background tasks via Celery** — Slow operations (AI inference, PDF rendering, file processing) are pushed to the worker. The API returns task IDs for polling when needed.
6. **pgvector for semantic search** — Document embeddings are stored as vectors in PostgreSQL for similarity search (HNSW index for O(log n) ANN queries).
7. **MinIO for file storage** — S3-compatible; production can swap to AWS S3 with a config change.
8. **Fine-tuned models shadow-deploy first** — `ml_models` table tracks model versions. Shadow mode routes 10% of traffic; promotion requires ≥100 calls and >5pp match-rate improvement. See `api/app/services/model_ab.py`.
9. **Variance closes the loop** — Actual job costs (`EstimateOutcome.actual_total`) feed the `pricing_corrections.py` engine, which emits advisory `PricingRecommendation` records. Admin approval required before any correction is applied.
10. **Offline-first for field** — `/field/*` routes use service worker pre-caching and `outbox.ts` IndexedDB queue for offline estimate creation and background sync.
11. **Auto-seeding** — The API seeds canonical suppliers, products, labor templates, markup rules, tax rates, permit costs, and city zone multipliers on first startup if the database is empty.
12. **Price enrichment cache** — Background warming at startup + periodic refresh every `price_cache_ttl_hours` (default 24h). Exposed via `/health` and admin refresh endpoint.

---

## Database Migrations

- **Tool:** Alembic
- **Source of truth:** `api/alembic/versions/`
- **Run after every schema change:** `alembic upgrade head`
- **Models registration:** `api/alembic/env.py` imports `app.models.*` to register metadata
- **Sync DSN override:** Alembic uses `DATABASE_URL_SYNC` (falls back to `DATABASE_URL` with `asyncpg` → `psycopg2` replacement)

---

## Deployment

### Production Stack

- Host OS: Ubuntu 22.04 LTS
- Orchestration: Docker Compose with `docker-compose.yml` + `docker-compose.prod.yml`
- Reverse proxy: Nginx (`deploy/nginx-ctlplumbingllc.conf`)
- TLS: Cloudflare terminates public SSL; origin handles Cloudflare→origin SSL on 443
- Domain: `app.ctlplumbingllc.com`
- Failover: Nginx upstream includes a backup server at `192.168.1.71` (ASUS Docker) for LAN/Tailscale resilience

### Environment Files

1. `.env` — Docker Compose variables (DB passwords, API keys, ports)
2. `deploy/runtime.env` — Host-level script variables (used by `scripts/run-api.sh`, `scripts/run-web.sh`)

### Production Differences

- `ENVIRONMENT=production`
- `LOG_LEVEL=WARNING`
- CORS locked to `https://app.ctlplumbingllc.com`
- Source volumes are **not** mounted (immutable containers)
- Worker log level: `warning`
- Cloudflare caching: 1-day TTL for HTML pages; deploy script purges cache after each release (`scripts/purge-cloudflare-cache.sh`)

### Helper Scripts

| Script | Purpose |
|---|---|
| `scripts/run-api.sh` | Run API with host-level env |
| `scripts/run-web.sh` | Run Next.js standalone server with host-level env |
| `scripts/run-worker.sh` | Run Celery worker with host-level env |
| `scripts/rebuild-web-clean.sh` | Archive old `node_modules`/`.next`, run `npm ci` + `npm run build:prod` |
| `scripts/deploy-web.sh` | Deploy web build and purge Cloudflare cache |
| `scripts/db-backup.sh` | PostgreSQL backup |
| `scripts/db-restore-drill.sh` | Restore drill for disaster recovery |
| `scripts/validate-env.sh` | Validate environment setup |

---

## Security Considerations

### Secrets & Environment Validation

- `SECRET_KEY` must be ≥ 32 random characters in production. The API fails fast at startup if it detects insecure defaults (`change-me`, `dev-secret`, etc.) when `ENVIRONMENT=production`.
- Never commit secrets. `.env` and `deploy/runtime.env` are in `.gitignore`.
- `SENTRY_DSN` and `RESEND_API_KEY` are optional but warned in production if missing.

### Auth

- JWT access tokens expire in 60 minutes (configurable).
- JWT refresh tokens expire in 30 days (configurable).
- Passwords hashed with bcrypt.
- Rate limiting via `slowapi` on LLM and public endpoints.

### Data Retention & Privacy

- Uploaded content (blueprints, photos, documents) retained for max **90 days** by default (`DATA_RETENTION_DAYS`).
- Soft-deleted records are hard-deleted after a **7-day** grace window (`SOFT_DELETE_GRACE_DAYS`).
- Daily Celery beat task: `worker.tasks.privacy.purge_expired_uploads`.
- Audit logs for every delete via structlog.

### CORS & Headers

- CORS origins are explicitly listed in `.env` (`CORS_ORIGINS`).
- Next.js frontend sends cache-control headers for Cloudflare edge caching; HTML pages get `s-maxage=86400`.
- Content-Security-Policy is set report-only via `next.config.ts` headers.
- Nginx adds `X-Frame-Options`, `X-Content-Type-Options`, `X-XSS-Protection`, and `Referrer-Policy`.
- `client_max_body_size 100M` in nginx for blueprint uploads.

---

## Environment Variables

### Required

| Variable | Description |
|---|---|
| `SECRET_KEY` | JWT signing key (≥ 32 random chars) |
| `DATABASE_URL` | Async PostgreSQL DSN (`postgresql+asyncpg://...`) |
| `REDIS_URL` | Redis connection string |
| `MINIO_ENDPOINT` | MinIO host:port |
| `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` | MinIO credentials |
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `DEEPSEEK_API_KEY` | At least one AI provider key for cloud fallback |

### Optional / Important

| Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | `development` or `production` |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `DEFAULT_LLM_PROVIDER` | `openai` | `openai`, `anthropic`, or `deepseek` |
| `DEFAULT_LLM_MODEL` | `gpt-4o-mini` | Model name |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | JWT access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | JWT refresh token lifetime |
| `CORS_ORIGINS` | `http://localhost:3000` | JSON array of allowed origins |
| `HERMES_ENDPOINT_URL` | `http://localhost:11434/v1` | Local Ollama endpoint |
| `LLM_PRIMARY_MODEL` | `qwen3:8b` | Primary local LLM |
| `LLM_SECONDARY_MODEL` | `hermes3:3b` | Fast fallback local LLM |
| `SENTRY_DSN` | — | Error telemetry |
| `RESEND_API_KEY` | — | Email delivery for proposals |
| `DATA_RETENTION_DAYS` | `90` | Max age of uploaded files |
| `SOFT_DELETE_GRACE_DAYS` | `7` | Grace period before hard deletion |
| `FERGUSON_CLIENT_ID` / `FERGUSON_CLIENT_SECRET` | — | Ferguson Trade API OAuth2 |
| `FERGUSON_API_VERIFY_MODE` | `off` | `strict`, `lenient`, or `off` |
| `ADOBE_CLIENT_ID` / `ADOBE_CLIENT_SECRET` | — | Adobe Document Cloud OAuth2 |
| `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` | — | Web Push VAPID keys |
| `ML_FINETUNE_ENABLED` | `False` | Master switch for LLM fine-tuning |

---

## Conventions & Patterns

### Adding a New API Endpoint

1. Define Pydantic schemas in `api/app/schemas/`.
2. Implement business logic in `api/app/services/`.
3. Create a router in `api/app/routers/` (or extend an existing one). Use `api/app/routers/v3/` for new v3 endpoints.
4. Register the router in `api/app/main.py` under the appropriate prefix.
5. Add tests in `api/tests/` (flat or under `routers/` / `services/`).
6. Run `pytest` and `ruff check .` before committing.

### Adding a Celery Task

1. Create or edit a module in `worker/tasks/`.
2. Import the task module in `worker/worker.py` (`include` list).
3. Add route in `worker/worker.py` `task_routes` if it should go to a specific queue (`default`, `high`, `ml`).
4. Add tests in `worker/tests/`.
5. Run `pytest -c pytest-worker.ini`.

### Adding a Frontend Page

1. Add the page under `web/src/app/` (App Router file-based routing).
2. Reuse components from `web/src/components/`.
3. Use `@tanstack/react-query` for data fetching.
4. Add unit tests next to the component (`*.test.tsx`) if logic is non-trivial.
5. Run `npm run lint` and `npm run test` before committing.

### Adding or Modifying a Form

1. Use `react-hook-form` for any non-trivial form (more than one field or with validation).
2. Define the zod schema in `web/src/lib/forms/schemas.ts` (or a domain-specific file under `web/src/lib/forms/` if it is not reusable).
3. Resolve the schema with `@hookform/resolvers/zod`.
4. Use shared primitives (`Input`, `Select`, `Button`, `FormLayout`, `FormSection`) and wire `aria-invalid`/`aria-describedby` via the `error` prop.
5. Keep validation logic out of component state; derive submit disabled state from `formState.isValid`/`isSubmitting` when appropriate.
6. Add schema unit tests in `web/src/lib/forms/*.test.ts`.
7. Run `npm run lint`, `npx tsc --noEmit`, and `npm run test` before committing.

### Database Changes

1. Update SQLAlchemy models in `api/app/models/`.
2. Generate a migration: `alembic revision --autogenerate -m "description"`
3. Review the generated migration file in `api/alembic/versions/`.
4. Apply: `alembic upgrade head`
5. Commit the migration file.

### Performance Budget

The frontend has a documented performance budget in `docs/PERFORMANCE_BUDGET.md`. Each route has a First Load JS ceiling. PRs that exceed a route budget must justify the increase or land an offsetting reduction. Refresh the baseline with `cd web && npm run build:prod`. The `npm run perf:budget` script enforces bundle-size limits.

---

## Useful Resources

- `README.md` — Quick start, architecture diagram, seeding instructions
- `docs/ARCHITECTURE.md` — Deep dive into system design, database schema, service responsibilities
- `docs/DEPLOYMENT.md` — Production deployment steps, Docker Compose overrides, nginx config
- `docs/API.md` — Full API reference with request/response examples
- `docs/API_ERRORS.md` — Error status code catalog and recovery strategies
- `docs/PERFORMANCE_BUDGET.md` — Per-route First Load JS baseline and budget table
- `docs/PRIVACY.md` — Data retention policy and audit logging
- `CHANGELOG.md` — Release notes and recent changes
- `plan-enhance-pricing-ai-chat.md` — v6.0 chat AI enhancement plan
- `docs/plans/2026-06-10-chat-ai-phases-9-14.md` — Phases 9–14 chat implementation plan
- `docs/plans/2026-06-11-pricing-chat-v7-roadmap.md` — v7.0 pricing-chat roadmap
- `docs/adr/` — Architecture Decision Records (finetune pipeline, PWA offline)

---

## Installed Skills

| Skill | Path | Purpose |
|---|---|---|
| iterate | `.agents/skills/iterate/` | Drive PR through CI, review, QA to merge |
| agent-memory | `.agents/skills/agent-memory/` | Persist/retrieve repo knowledge |
| code-review | `.agents/skills/code-review/` | Rigorous PR code review |
| docker | `.agents/skills/docker/` | Docker daemon + container management |
| github | `.agents/skills/github/` | GitHub API/CLI interactions |
| agent-creator | `.agents/skills/agent-creator/` | Guided workflow to create sub-agents |
| code-simplifier | `.agents/skills/code-simplifier/` | Simplify and refine code |
| openhands-automation | `.agents/skills/openhands-automation/` | Create cron/webhook automations |
| github-pr-review | `.agents/skills/github-pr-review/` | Post PR review comments via GitHub API |
| qa-changes | `.agents/skills/qa-changes/` | Structured QA methodology for PRs |
| release-notes | `.agents/skills/release-notes/` | Generate changelogs from git history |
| learn-from-code-review | `.agents/skills/learn-from-code-review/` | Distill PR feedback into reusable skills |
| prd | `.agents/skills/prd/` | Generate Product Requirements Documents |
| agent-sdk-builder | `.agents/skills/agent-sdk-builder/` | Guided workflow for building custom agents |
| openhands-sdk | `.agents/skills/openhands-sdk/` | OpenHands Software Agent SDK reference |
| kubernetes | `.agents/skills/kubernetes/` | Local K8s clusters via KIND |
| vercel | `.agents/skills/vercel/` | Vercel deployment & management |
| uv | `.agents/skills/uv/` | Python dependency/environment management |
| npm | `.agents/skills/npm/` | npm package installation in non-interactive envs |
| swift-linux | `.agents/skills/swift-linux/` | Swift installation on Debian Linux |
| frontend-design | `.agents/skills/frontend-design/` | Production-grade frontend UI design |
| theme-factory | `.agents/skills/theme-factory/` | Theming toolkit for artifacts |
| pdflatex | `.agents/skills/pdflatex/` | Compile LaTeX to PDF |
| openhands-api | `.agents/skills/openhands-api/` | OpenHands Cloud REST API (V1) |

*Keep this file accurate. When you add new infrastructure, change build commands, or modify testing strategy, update this guide.*
