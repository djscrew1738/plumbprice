# PlumbPrice AI — Agent Guide

This file is the canonical reference for AI coding agents working in this repository. It describes the project structure, build commands, testing strategy, code conventions, and security rules. Read this before making any non-trivial change.

---

## Project Overview

PlumbPrice AI is an autonomous plumbing pricing and estimating platform for DFW-area plumbing contractors. It replaces spreadsheet-based estimating with a chat-driven interface that produces itemized, line-level quotes backed by real supplier pricing data. The system guarantees that every price shown can be traced directly to a supplier SKU and a labor template — the LLM extracts intent and maps it to canonical line items, but all dollar math happens in pure Python with no LLM involvement.

Current version: **5.8.0**

---

## Technology Stack

| Layer | Technology |
|---|---|
| API | FastAPI (Python 3.12), async-first |
| Database | PostgreSQL 16 + pgvector |
| Cache / Queue broker | Redis 7 |
| Task worker | Celery 5 (Python) |
| Object storage | MinIO (S3-compatible) |
| Frontend | Next.js 15 (App Router, TypeScript, React 19) |
| Styling | Tailwind CSS 3, Framer Motion, Lucide React |
| AI / LLM | OpenAI GPT-4o, Anthropic Claude, Ollama (local) |
| Auth | JWT (access + refresh tokens), passlib+bcrypt |

---

## Repository Layout

```
.
├── api/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py         # FastAPI app factory, middleware, routers
│   │   ├── config.py       # Pydantic-settings configuration
│   │   ├── database.py     # SQLAlchemy async engine + session
│   │   ├── observability.py# Structlog setup, Sentry init
│   │   ├── models/         # SQLAlchemy ORM models (~30 tables)
│   │   ├── routers/        # FastAPI route modules (30+ routers)
│   │   ├── schemas/        # Pydantic request/response models
│   │   ├── services/       # Business logic, external integrations
│   │   └── core/           # Auth, storage, cache, rate limit, exceptions
│   ├── alembic/            # Database migrations (Alembic)
│   ├── tests/              # pytest suite (API + service tests)
│   ├── scripts/            # Seed script, admin creation
│   ├── requirements.txt    # Runtime + dev dependencies
│   ├── Dockerfile          # Python 3.12 slim
│   └── pyproject.toml      # pytest, coverage config
│
├── web/                    # Next.js frontend
│   ├── src/
│   │   ├── app/            # App Router pages (Next.js 15)
│   │   ├── components/     # React components
│   │   ├── lib/            # API clients, utilities
│   │   ├── contexts/       # React context providers
│   │   ├── types/          # Shared TypeScript types
│   │   └── test/           # Vitest setup file
│   ├── tests/e2e/          # Playwright end-to-end tests
│   ├── public/             # Static assets
│   ├── package.json
│   ├── next.config.ts      # Standalone output, rewrites, headers, Sentry
│   ├── vitest.config.ts    # Unit test config (jsdom, v8 coverage)
│   ├── playwright.config.ts# E2E test config
│   └── Dockerfile          # Multi-stage Node 20 build
│
├── worker/                 # Celery background worker
│   ├── tasks/              # Celery task modules
│   │   ├── supplier_refresh.py
│   │   ├── document_processing.py
│   │   ├── blueprint_analysis.py
│   │   └── privacy.py
│   ├── tests/              # Worker-specific pytest tests
│   ├── worker.py           # Celery app factory + beat schedule
│   ├── requirements.txt
│   └── Dockerfile
│
├── scripts/                # Host-level deployment & utility scripts
├── deploy/                 # Nginx config, runtime.env.example
├── docs/                   # Architecture, API ref, deployment, privacy, perf budget
├── docker-compose.yml      # Local dev stack (all services)
├── docker-compose.prod.yml # Production overrides
├── .env.example            # Required environment variables
├── pytest.ini              # API test config
└── pytest-worker.ini       # API + worker combined test config
```

---

## Build & Development Commands

### Docker Compose (recommended for local development)

```bash
# Start all services (postgres, redis, minio, api, worker, web)
docker compose up -d

# Run migrations inside the API container
docker compose exec api alembic upgrade head

# Seed the database with demo data
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

### Frontend (local Node)

```bash
cd web
npm install

# Dev server (Turbopack)
npm run dev

# Production build
npm run build:prod

# Clean rebuild (archives old node_modules/.next, runs npm ci + build)
../scripts/rebuild-web-clean.sh
```

---

## Testing Instructions

### API Tests

```bash
cd api
pytest                              # Run all API tests
pytest -k "substring"              # Run tests matching a name
pytest tests/routers/test_chat.py  # Run a specific file
```

- Config: `api/pyproject.toml`
- Default DB for tests: in-memory SQLite (`sqlite+aiosqlite:///:memory:`)
- Rate limiting is disabled in tests via `limiter.enabled = False`
- Current coverage floor: **30%** (`fail_under = 30`)
- Markers: `asyncio`, `integration`, `unit`

### Worker Tests

```bash
# From repo root (uses pytest-worker.ini)
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

- Config: `vitest.config.ts`
- Environment: `jsdom`
- Coverage thresholds: lines 50%, functions 50%, branches 40%, statements 50%
- Setup file: `src/test/setup.ts` (extends `@testing-library/jest-dom`, stubs `matchMedia`)

### Frontend E2E Tests

```bash
cd web
npm run test:e2e            # Headless Playwright run
npx playwright test --ui    # Interactive UI mode
```

- Config: `playwright.config.ts`
- Browsers: Chromium, Firefox, WebKit
- Base URL: `http://localhost:3000`

---

## Code Style Guidelines

### Python

- **Formatter / Linter**: `ruff check .` and `ruff format .`
- **Type checker**: `mypy app/`
- **Async-first**: All database access uses SQLAlchemy async sessions (`AsyncSession`) and `asyncpg`. Endpoints and services should be `async def` unless there is a clear reason not to.
- **Structured logging**: Use `structlog.get_logger()`; do not use raw `print()` or standard `logging` directly.
- **Import style**: Absolute imports from `app.*` inside `api/`; relative imports inside `worker/`.

### TypeScript / React

- **Linter**: `eslint` with `next/core-web-vitals` and `next/typescript` (config in `eslint.config.mjs`)
- **Strict mode**: Enabled in `tsconfig.json` (`strict: true`, `noImplicitOverride: true`)
- **Path alias**: `@/*` maps to `src/*`
- **React patterns**: Prefer functional components with hooks. Use `React.memo` for stable UI primitives. Lazy-load heavy components with `next/dynamic` where appropriate.
- **Data fetching**: Use `@tanstack/react-query` for server state; use `axios` for raw HTTP calls.

---

## Architecture & Design Principles

### Service Architecture

```
Browser (Next.js 15, port 3000)
    │ HTTPS / REST
    ▼
FastAPI (port 8000) — /api/v1/* and /api/v3/*
    │ async DB queries           │ enqueue tasks
    ▼                            ▼
PostgreSQL + pgvector      Redis (broker + cache)
                                │
                                ▼
                         Celery Worker (default queue)
                         - supplier_refresh (daily beat)
                         - document_processing
                         - blueprint_analysis
                         - privacy.purge_expired_uploads
                         - price_forecast (weekly beat)  ← v4.1
                                │
                         Celery Worker ML (ml queue)    ← v4.1
                         - finetune.run_finetune
                         - finetune.poll_finetune_job
                                │
                                ▼
                         MinIO (object storage)
                         blueprints / documents / proposals / photos
```

### Key Design Decisions

1. **Deterministic pricing** — The LLM extracts intent and maps to canonical line items. All dollar math is pure Python; the same inputs always produce the same output.
2. **Full traceability** — Every line item carries a `trace_json` blob with supplier, SKU, cost, labor template, and multipliers.
3. **Confidence transparency** — Estimates surface a 0.0–1.0 confidence score and a human-readable label (High / Medium / Low / Estimate-Only).
4. **Async-first API** — SQLAlchemy async sessions + asyncpg for I/O-bound endpoints.
5. **Background tasks via Celery** — Slow operations (AI inference, PDF rendering, file processing) are pushed to the worker. The API returns task IDs for polling when needed.
6. **pgvector for semantic search** — Document embeddings are stored as vectors in PostgreSQL for similarity search (HNSW index added in v4.1 for O(log n) ANN queries).
7. **MinIO for file storage** — S3-compatible; production can swap to AWS S3 with a config change.
8. **Fine-tuned models shadow-deploy first** — `ml_models` table tracks model versions. Shadow mode routes 10% of traffic; promotion requires ≥100 calls and >5pp match-rate improvement. See `api/app/services/model_ab.py`.
9. **Variance closes the loop** — Actual job costs (`EstimateOutcome.actual_total`) feed the `pricing_corrections.py` engine, which emits advisory `PricingRecommendation` records. Admin approval required before any correction is applied.
10. **Offline-first for field** — `/field/*` routes use service worker pre-caching and `outbox.ts` IndexedDB queue for offline estimate creation and background sync.

### Database Migrations

- **Tool**: Alembic
- **Source of truth**: `api/alembic/versions/`
- **Run after every schema change**: `alembic upgrade head`
- **Models registration**: `api/alembic/env.py` imports `app.models.*` to register metadata
- **Sync DSN override**: Alembic uses `DATABASE_URL_SYNC` (falls back to `DATABASE_URL` with `asyncpg` → `psycopg2` replacement)

---

## Deployment

### Production Stack

- Host OS: Ubuntu 22.04 LTS recommended
- Orchestration: Docker Compose with `docker-compose.yml` + `docker-compose.prod.yml`
- Reverse proxy: Nginx (`deploy/nginx-ctlplumbingllc.conf`)
- TLS: Cloudflare terminates public SSL; origin handles Cloudflare→origin SSL on 443
- Domain: `app.ctlplumbingllc.com`

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
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `DEEPSEEK_API_KEY` | At least one AI provider key |

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
| `SENTRY_DSN` | — | Error telemetry |
| `RESEND_API_KEY` | — | Email delivery for proposals |
| `DATA_RETENTION_DAYS` | `90` | Max age of uploaded files |
| `SOFT_DELETE_GRACE_DAYS` | `7` | Grace period before hard deletion |

---

## Conventions & Patterns

### Pricing Engine (v5.8.0 Expansion)

The pricing engine now supports **500+ SKUs** across 7 categories and **150+ labor templates**:

- **Categories**: commercial_fixture, smart_plumbing, medical_healthcare, restaurant_kitchen, industrial, outdoor_irrigation, piping_fittings
- **Bulk Import**: Admins can upload CSVs via `POST /admin/pricing/bulk-import/products` and `/labor` with dry-run preview
- **Price Feeds**: Generic `PriceFeedAdapter` framework with Ferguson (OAuth2/simulation), Kohler, Moen, and AO Smith scrapers
- **Feed Health**: `GET /admin/pricing/feeds/health` returns adapter status
- **Catalog Browser**: `GET /admin/pricing/catalog` with search, filter by category/supplier
- **Seed Scripts**: `api/scripts/seed_expanded_catalog.py` populates expanded catalog from JSON data files

### Adding a New API Endpoint

1. Define Pydantic schemas in `api/app/schemas/`.
2. Implement business logic in `api/app/services/`.
3. Create a router in `api/app/routers/` (or extend an existing one).
4. Register the router in `api/app/main.py` under `/api/v1`.
5. Add tests in `api/tests/` (flat or under `routers/` / `services/`).
6. Run `pytest` and `ruff check .` before committing.

### Adding a Celery Task

1. Create or edit a module in `worker/tasks/`.
2. Import the task module in `worker/worker.py` (`include` list).
3. Add tests in `worker/tests/`.
4. Run `pytest -c pytest-worker.ini`.

### Adding a Frontend Page

1. Add the page under `web/src/app/` (App Router file-based routing).
2. Reuse components from `web/src/components/`.
3. Use `@tanstack/react-query` for data fetching.
4. Add unit tests next to the component (`*.test.tsx`) if logic is non-trivial.
5. Run `npm run lint` and `npm run test` before committing.

### Database Changes

1. Update SQLAlchemy models in `api/app/models/`.
2. Generate a migration: `alembic revision --autogenerate -m "description"`
3. Review the generated migration file in `api/alembic/versions/`.
4. Apply: `alembic upgrade head`
5. Commit the migration file.

### Performance Budget

The frontend has a documented performance budget in `docs/PERFORMANCE_BUDGET.md`. Each route has a First Load JS ceiling (roughly +10% over the 2.5.1 baseline). PRs that exceed a route budget must justify the increase or land an offsetting reduction. Refresh the baseline with `cd web && npm run build:prod`.

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
