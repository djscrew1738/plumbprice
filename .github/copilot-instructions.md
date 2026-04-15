# Copilot instructions for PlumbPrice AI

This file collects repository-specific hints for AI assistants (Copilot CLI / copilots) to work productively in this repository.

---

## 1) Quick build, test, and lint commands

API (FastAPI, Python)
- Install: cd api && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
- Run dev server: cd api && uvicorn app.main:app --reload --port 8000
- Run migrations: alembic upgrade head (run from repository root or api/ as appropriate)
- Run API tests (all): cd api && pytest
- Run a single API test: cd api && pytest path/to/test_file.py::test_function  OR pytest -k "substring_of_test_name"
- Lint/format Python: cd api && ruff check .  ; ruff format .  ; mypy app/

Worker (Celery)
- Start worker (backing services must be running): celery -A worker worker --loglevel=debug --concurrency=2
- Worker package requirements live in worker/requirements.txt (or reuse api/.venv)

Frontend (Next.js)
- Install & run dev: cd web && npm install && npm run dev
- Run frontend tests (Jest): cd web && npm test
- Run a single frontend test: cd web && npm test -- -t "test name substring"
- Clean rebuild helper: ./scripts/rebuild-web-clean.sh
- Lint frontend: cd web && npm run lint

Docker / Compose
- Start everything (recommended): docker compose up -d
- Start core backing services only: docker compose -f docker-compose.yml up -d postgres redis minio
- Run a command inside the api container: docker compose exec api <command>
- Run migrations inside the container: docker compose exec api alembic upgrade head

Seeding & reset
- Seed DB (docker): docker compose exec api python -m app.scripts.seed
- Seed DB (local): cd api && python -m app.scripts.seed
- Reset DB (destructive): docker compose down -v && docker compose up -d postgres && docker compose exec api alembic upgrade head && docker compose exec api python -m app.scripts.seed

---

## 2) High-level architecture (short summary)

- Monorepo split into three primary services:
  - api/: FastAPI backend (async-first, SQLAlchemy async + asyncpg, Alembic migrations)
  - worker/: Celery worker processes (vision/OCR, embedding generation, PDF rendering, background tasks)
  - web/: Next.js frontend (App Router)

- Supporting infrastructure (via docker-compose): PostgreSQL (with pgvector for embeddings), Redis (broker/cache), MinIO (S3 object storage).
- AI providers are pluggable (OpenAI, Anthropic) via env variables and a provider abstraction in the API.
- Key flows: frontend -> API (/api/v1) -> enqueue heavy tasks to Celery -> worker stores artifacts in MinIO and writes results to PostgreSQL; embeddings live in pgvector for semantic search.

---

## 3) Key repository conventions and patterns

- API prefix and routing: endpoints are expected to be under `/api/v1` — follow existing route structure when adding endpoints.
- Async-first Python: database access and IO in the api/ codebase use async SQLAlchemy sessions and asyncpg. Prefer async functions in endpoints and services unless a clear reason exists.
- Background work: push long-running or blocking tasks (AI calls, OCR, PDF generation) to Celery tasks (worker/). Keep request handlers fast and return task IDs for polling when appropriate.
- Migrations: Alembic is the source of truth. Always run alembic upgrade head after schema changes; include migration files in VCS.
- Seeding & test fixtures: app.scripts.seed provides a reproducible dataset for dev; tests may rely on similar fixtures—use the seed for manual testing and local demos.
- Environment management: copy .env.example -> .env and fill required keys. Secrets must not be committed.
- Packaging and virtualenvs: api/ and worker/ may share a virtualenv. Follow the README's activation steps for deterministic development.
- Vector search: embeddings are stored in PostgreSQL via pgvector. When adding document/embedding code, use the existing embedding helpers and store vectors into the DB column type used by pgvector.
- File storage: uploaded blueprints, generated PDFs and other artifacts are stored in MinIO buckets (blueprints, documents, proposals). Use the storage abstraction/config so swapping S3 is straightforward.
- Tests: API tests run with pytest inside api/; frontend tests are run via npm in web/.

---

## 4) Files, scripts, and helpers worth knowing (non-exhaustive)
- docker-compose.yml — local composition of services used by Docker-based dev/test.
- .env.example — required environment variables and defaults
- scripts/rebuild-web-clean.sh — clean/rebuild helper for the Next.js app
- run_backend_optimizations.sh, start-api.sh — local helper scripts for backend operations
- app.scripts.seed — seed script used to populate demo data
- README.md — contains quick-start, architecture diagram, and common commands (use as canonical source for run commands)

---

## 5) AI / assistant integration notes
- No CLAUDE.md, AGENTS.md, or other assistant-specific files were detected in the repository root when these instructions were generated. If such files are later added, include their salient parts into this instructions file.
- When interacting with the codebase, fetch README.md first for quick context (architecture and common commands are kept there).

---

If this file already existed, prefer updating rather than replacing: keep any project-specific Copilot config snippets. When updating, merge rather than overwrite.

---

Summary
- This file lists the most-used build/test/lint commands, the high-level architecture, and repository conventions that affect changes across multiple files. Keep it current when adding new infra (e.g., switching Redis for a managed cache) or new test systems.

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
