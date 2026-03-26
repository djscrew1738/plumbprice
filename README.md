# PlumbPrice AI

An autonomous plumbing pricing and estimating platform powered by AI. PlumbPrice AI enables plumbing contractors to generate accurate, professional estimates from blueprints and project descriptions using large language models and computer vision.

---

## Table of Contents

- [Overview](#overview)
- [Quick Start with Docker Compose](#quick-start-with-docker-compose)
- [Environment Setup](#environment-setup)
- [Architecture Overview](#architecture-overview)
- [API Endpoints Summary](#api-endpoints-summary)
- [Development Setup](#development-setup)
- [Seeding the Database](#seeding-the-database)

---

## Overview

PlumbPrice AI provides plumbing contractors with:

- **AI-powered blueprint analysis** — Upload PDF blueprints and let the AI identify fixtures, pipe runs, and material requirements.
- **Automated cost estimation** — Line-item estimates with regional pricing data, labor rates, and material costs.
- **Proposal generation** — Professional PDF proposals generated from estimates, ready to send to clients.
- **Knowledge base** — Upload past bids, spec sheets, and product catalogs to ground the AI in your company's pricing.
- **Chat interface** — Ask natural language questions about any project or estimate.

### Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI (Python 3.12, async) |
| Database | PostgreSQL 16 + pgvector |
| Cache / Queue broker | Redis 7 |
| Task worker | Celery 5 |
| Object storage | MinIO (S3-compatible) |
| Frontend | Next.js 14 (App Router) |
| AI | OpenAI GPT-4o / Anthropic Claude |

---

## Quick Start with Docker Compose

### Prerequisites

- Docker 24+ and Docker Compose v2
- An OpenAI or Anthropic API key

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/your-org/plumbprice-ai.git
cd plumbprice-ai

# 2. Copy and configure environment variables
cp .env.example .env
# Edit .env and set at minimum:
#   OPENAI_API_KEY or ANTHROPIC_API_KEY
#   SECRET_KEY (generate with: openssl rand -hex 32)

# 3. Start all services
docker compose up -d

# 4. Run database migrations
docker compose exec api alembic upgrade head

# 5. (Optional) Seed the database with sample data
docker compose exec api python -m app.scripts.seed

# 6. Open the app
open http://localhost:3000
```

The API documentation is available at http://localhost:8000/docs (Swagger UI) and http://localhost:8000/redoc.

To start Flower (Celery task monitor) during development:

```bash
docker compose --profile dev up -d
open http://localhost:5555
```

---

## Environment Setup

Copy `.env.example` to `.env` and fill in all required values:

```bash
cp .env.example .env
```

### Required Variables

| Variable | Description |
|---|---|
| `SECRET_KEY` | JWT signing key. Generate with `openssl rand -hex 32`. |
| `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` | At least one AI provider key is required. |
| `POSTGRES_PASSWORD` | Change from default in any non-local environment. |
| `MINIO_ROOT_PASSWORD` | Change from default in any non-local environment. |

### Optional Variables

| Variable | Default | Description |
|---|---|---|
| `DEFAULT_LLM_PROVIDER` | `openai` | Which AI provider to use (`openai` or `anthropic`). |
| `DEFAULT_LLM_MODEL` | `gpt-4o-mini` | Model name for the selected provider. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | JWT access token lifetime. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | JWT refresh token lifetime. |
| `LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated list of allowed CORS origins. |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client (Browser)                         │
│                    Next.js 14 — port 3000                       │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP / REST
┌────────────────────────────▼────────────────────────────────────┐
│                     FastAPI — port 8000                         │
│  /auth  /projects  /estimates  /proposals  /documents  /chat    │
└───────┬────────────────┬───────────────────────────────────────-┘
        │                │
        │ async          │ enqueue tasks
┌───────▼──────┐  ┌──────▼──────────────────────────────────────┐
│  PostgreSQL  │  │           Redis (broker + cache)             │
│  + pgvector  │  └──────┬──────────────────────────────────────-┘
└──────────────┘         │ consume tasks
                  ┌──────▼──────────────────────────────────────┐
                  │         Celery Worker                        │
                  │  - Blueprint OCR / vision analysis           │
                  │  - Embedding generation                      │
                  │  - PDF proposal rendering                    │
                  │  - Pricing data refresh                      │
                  └──────┬──────────────────────────────────────┘
                         │
                  ┌──────▼──────────────────────────────────────┐
                  │   MinIO (S3-compatible object storage)       │
                  │   Buckets: blueprints, documents, proposals  │
                  └─────────────────────────────────────────────┘
```

### Key Design Decisions

- **Async-first API**: All database queries use SQLAlchemy async sessions with asyncpg to maximize throughput on I/O-bound operations.
- **Background tasks via Celery**: Slow operations (AI inference, PDF rendering, file processing) are pushed to the Celery worker so the API stays responsive.
- **pgvector for semantic search**: Document embeddings are stored as vectors in PostgreSQL enabling similarity search for the knowledge base and context retrieval.
- **MinIO for file storage**: Blueprints, generated proposals, and uploaded documents are stored in MinIO, which is fully S3-compatible so production deployments can swap in AWS S3 or any S3-compatible service with a config change.

---

## API Endpoints Summary

All endpoints are prefixed with `/api/v1`.

### Authentication

| Method | Path | Description |
|---|---|---|
| `POST` | `/auth/register` | Create a new user account. |
| `POST` | `/auth/login` | Exchange credentials for JWT tokens. |
| `POST` | `/auth/refresh` | Refresh an expired access token. |
| `POST` | `/auth/logout` | Invalidate the current refresh token. |
| `GET` | `/auth/me` | Return the current authenticated user. |

### Projects

| Method | Path | Description |
|---|---|---|
| `GET` | `/projects` | List all projects for the current user. |
| `POST` | `/projects` | Create a new project. |
| `GET` | `/projects/{id}` | Get project details. |
| `PATCH` | `/projects/{id}` | Update project metadata. |
| `DELETE` | `/projects/{id}` | Archive a project. |
| `POST` | `/projects/{id}/blueprints` | Upload blueprint files for a project. |

### Estimates

| Method | Path | Description |
|---|---|---|
| `GET` | `/estimates` | List estimates (filterable by project). |
| `POST` | `/estimates` | Generate a new estimate (triggers AI analysis). |
| `GET` | `/estimates/{id}` | Get estimate with all line items. |
| `PATCH` | `/estimates/{id}` | Update line items or totals manually. |
| `POST` | `/estimates/{id}/approve` | Mark an estimate as approved. |

### Proposals

| Method | Path | Description |
|---|---|---|
| `POST` | `/proposals` | Generate a PDF proposal from an estimate. |
| `GET` | `/proposals/{id}` | Get proposal metadata. |
| `GET` | `/proposals/{id}/download` | Download the generated PDF. |
| `POST` | `/proposals/{id}/send` | Email the proposal to a client. |

### Documents (Knowledge Base)

| Method | Path | Description |
|---|---|---|
| `GET` | `/documents` | List uploaded knowledge base documents. |
| `POST` | `/documents` | Upload a document (spec sheet, price list, etc.). |
| `DELETE` | `/documents/{id}` | Remove a document from the knowledge base. |

### Chat

| Method | Path | Description |
|---|---|---|
| `POST` | `/chat` | Send a message; returns an AI-generated response. |
| `GET` | `/chat/history` | Retrieve conversation history. |

### Tasks

| Method | Path | Description |
|---|---|---|
| `GET` | `/tasks/{task_id}` | Poll background task status and result. |

---

## Development Setup

### Prerequisites

- Python 3.12
- Node.js 20
- Docker and Docker Compose (for PostgreSQL, Redis, MinIO)

### API (FastAPI)

```bash
cd api

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp ../.env.example ../.env

# Start backing services only
docker compose -f ../docker-compose.yml up -d postgres redis minio

# Run migrations
alembic upgrade head

# Start the development server
uvicorn app.main:app --reload --port 8000
```

### Worker (Celery)

```bash
cd worker

# Reuse the same virtual environment or create a new one
source ../api/.venv/bin/activate

pip install -r requirements.txt

# Start the worker (backing services must already be running)
celery -A worker worker --loglevel=debug --concurrency=2
```

### Frontend (Next.js)

```bash
cd web

npm install

# Copy and configure the frontend environment
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

npm run dev
```

The frontend dev server is available at http://localhost:3000.

### Running Tests

```bash
# API tests
cd api
pytest

# Frontend tests
cd web
npm test
```

### Code Quality

```bash
# Lint and format Python
cd api
ruff check .
ruff format .

# Type-check Python
mypy app/

# Lint and format TypeScript/JS
cd web
npm run lint
```

---

## Seeding the Database

A seed script is included to populate the database with realistic sample data for development and demonstration purposes.

### What the seed creates

- 2 sample user accounts (`admin@example.com` / `password123` and `contractor@example.com` / `password123`)
- 3 sample projects with metadata
- Sample material cost items (fixtures, pipe, fittings)
- Sample labor rate configurations
- A sample estimate with line items for one of the projects

### Running the seed

```bash
# Using Docker Compose (recommended)
docker compose exec api python -m app.scripts.seed

# Or directly if running the API locally
cd api
python -m app.scripts.seed
```

### Resetting the database

To wipe all data and re-seed from scratch:

```bash
# Drop and recreate the database via Docker
docker compose down -v          # removes postgres_data volume
docker compose up -d postgres
docker compose exec api alembic upgrade head
docker compose exec api python -m app.scripts.seed
```

> Warning: `docker compose down -v` permanently deletes all database data and MinIO files. Do not run this against a production environment.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
