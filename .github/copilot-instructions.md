# Copilot Instructions — PlumbPrice AI

PlumbPrice AI is a plumbing estimating platform for DFW contractors. The LLM extracts intent and maps it to canonical line items; **all dollar math is pure Python** — the same inputs always produce the same price. Every line item carries a `trace_json` blob (supplier, SKU, cost, labor template, multipliers).

---

## Build, Test & Lint

### API (FastAPI / Python 3.12)

```bash
cd api
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

uvicorn app.main:app --reload --port 8000   # dev server

alembic upgrade head                        # run migrations

pytest                                      # all tests
pytest -k "substring"                       # single test by name
pytest tests/routers/test_chat.py::test_fn  # single test by path

ruff check . && ruff format .               # lint + format
mypy app/                                   # type check
```

### Worker (Celery)

```bash
source api/.venv/bin/activate
cd worker && pip install -r requirements.txt
celery -A worker worker --loglevel=info --concurrency=2

# Worker tests (from repo root):
pytest -c pytest-worker.ini
```

### Frontend (Next.js 15)

```bash
cd web
npm install
npm run dev                  # dev server (Turbopack)
npm run build:prod           # production build
../scripts/rebuild-web-clean.sh  # clean rebuild (archives old node_modules/.next)

npm run test                 # Vitest unit tests with coverage
npm run test:watch           # Vitest watch mode
npm test -- -t "test name"   # single test by name

npm run test:e2e             # Playwright headless
npx playwright test --ui     # Playwright interactive UI
npm run lint
```

### Docker Compose

```bash
docker compose up -d                         # start everything
docker compose up -d postgres redis minio    # backing services only
docker compose exec api alembic upgrade head
docker compose exec api python -m app.scripts.seed

# Full DB reset:
docker compose down -v && docker compose up -d postgres \
  && docker compose exec api alembic upgrade head \
  && docker compose exec api python -m app.scripts.seed
```

---

## Architecture

```
Browser (Next.js 15, :3000)
    │ REST /api/v1/*
    ▼
FastAPI (:8000)
    │ async SQLAlchemy          │ enqueue tasks
    ▼                           ▼
PostgreSQL + pgvector       Redis (broker + cache)
                                │
                                ▼
                         Celery Worker
                         ├── supplier_refresh (daily beat)
                         ├── document_processing
                         ├── blueprint_analysis
                         └── privacy.purge_expired_uploads
                                │
                                ▼
                         MinIO (blueprints / documents / proposals)
```

- All API routes are registered under `/api/v1`. A parallel `/api/v3` prefix exists for newer versioned endpoints (`api/app/routers/v3/`).
- AI providers (OpenAI, Anthropic, Ollama) are pluggable via `DEFAULT_LLM_PROVIDER` / `DEFAULT_LLM_MODEL` env vars and a service abstraction in `api/app/services/llm_service.py`.
- The LLM service uses a **dual-model circuit breaker**: primary `qwen3:8b`, fallback `hermes3:3b`, with a keyword-only classifier as last resort. Falls through gracefully if Ollama is unavailable.
- Confidence scores (0.0–1.0) and human-readable labels (High / Medium / Low / Estimate-Only) are surfaced on every estimate.
- **v3 agent rule**: the v3 agent (`services/agent_v3.py`) reasons, calls tools, and gathers data — the `PricingEngine` does all dollar math. Never put pricing calculations inside the agent; never call the LLM from the pricing engine.
- **Auto-seed on first run**: `_ensure_seeded()` in `main.py` seeds canonical suppliers, labor templates, and pricing rules automatically when the suppliers table is empty. This is distinct from the demo-data seed script (`app.scripts.seed`).

---

## Key Conventions

### Python / API

- **Async-first**: all DB access uses `AsyncSession` + `asyncpg`. Use `async def` for endpoints and services.
- **Structured logging**: `structlog.get_logger()` everywhere. Never use `print()` or stdlib `logging` directly.
- **Imports**: absolute (`app.*`) inside `api/`; relative inside `worker/`.
- **Domain errors**: raise `PricingError`, `SupplierError`, or `BlueprintError` (from `app.core.exceptions`) — these map to structured JSON error responses. Don't raise plain `HTTPException` for domain failures.
- **Async SQLAlchemy gotcha**: attributes are expired after `await db.commit()`. Re-accessing `obj.id` etc. raises `MissingGreenlet`. Always call `await db.refresh(obj)` after a commit, or capture needed values before the commit.

### Adding an endpoint

1. Schemas → `api/app/schemas/`
2. Business logic → `api/app/services/`
3. Router → `api/app/routers/` (or `routers/v3/` for versioned)
4. Register in `api/app/main.py` under the appropriate prefix
5. Tests → `api/tests/`

### Database changes

1. Edit models in `api/app/models/`
2. `alembic revision --autogenerate -m "description"` then review
3. `alembic upgrade head` — always commit the migration file

### Adding a Celery task

1. Create/edit a module in `worker/tasks/`
2. Add it to the `include` list in `worker/worker.py`
3. Tests in `worker/tests/` (tasks run synchronously via `task_always_eager = True`)

### TypeScript / React

- **Path alias**: `@/*` → `src/*`
- **Data fetching**: `@tanstack/react-query` for server state; `axios` for raw HTTP.
- **Safe queries**: use `useSafeQuery(options, fallback)` from `@/lib/hooks` for list queries — guarantees `data` is never `undefined`.
- **Error handling in components**: always handle `isError`. Pattern: `if (isLoading) return <Skeleton />; if (isError) return <ErrorState onRetry={() => void refetch()} />;`
- **Lazy loading**: use `next/dynamic` for heavy components.
- **API clients**: domain-specific modules live in `web/src/lib/api/` (e.g. `estimates.ts`, `blueprints.ts`). All are built with `createApiClient` from `@/lib/api/client`. Import from `@/lib/api` (barrel). For v3 endpoints use `apiV3` from `@/lib/api-v3`.
- **Auth cookie**: the JWT is stored as a `pp_token` HttpOnly cookie. On a 401, the axios interceptor dispatches a `pp:session-expired` custom event and redirects to `/login` after 3 s. Don't handle 401 redirects manually.
- **Network resilience**: for mutations that may fail on flaky connections, wrap the call with `withRetry(fn)` from `@/lib/withRetry` (3 attempts, exponential back-off, retries network errors + 408/429/5xx only). For offline queueing, use `enqueue` / `dequeue` from `@/lib/outbox` (Dexie/IndexedDB, gated by `flag:outbox_offline` localStorage flag).

### Adding a frontend page

1. Page file under `web/src/app/` (App Router)
2. Reuse components from `web/src/components/`
3. Unit tests co-located as `*.test.tsx` for non-trivial logic
4. Run `npm run lint && npm run test` before committing

### Performance budget

The frontend has per-route First Load JS ceilings in `docs/PERFORMANCE_BUDGET.md` (~+10% over v2.5.1 baseline). Refresh baseline with `cd web && npm run build`.

---

## Testing Notes

- **API tests**: use in-memory SQLite (`sqlite+aiosqlite:///:memory:`). Rate limiting is disabled via `limiter.enabled = False` in `conftest.py`. Coverage floor: 30% (`fail_under = 30` in `pyproject.toml`).
- **Set env vars before app imports**: `conftest.py` sets `DATABASE_URL`, `SECRET_KEY`, and `ENVIRONMENT=test` via `os.environ.setdefault` _before_ importing `app.*` to prevent asyncpg engine creation.
- **Worker tests**: `task_always_eager = True` — tasks run synchronously. Redis must be reachable.
- **Playwright config**: `web/playwright.config.ts` (Chromium, Firefox, WebKit). Base URL: `http://localhost:3000`.
- **Vitest config**: `web/vitest.config.ts`, jsdom environment, coverage thresholds: 50% lines/functions/statements, 40% branches.

---

## Environment

Copy `.env.example` → `.env`. Required keys: `SECRET_KEY` (≥32 chars), `DATABASE_URL` (`postgresql+asyncpg://...`), `REDIS_URL`, `MINIO_ENDPOINT/ACCESS_KEY/SECRET_KEY`, and at least one of `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`.

The API **fails fast at startup** in `ENVIRONMENT=production` if `SECRET_KEY` matches known dev defaults (`change-me`, `dev-secret`, etc.) or is shorter than 32 characters.
