# PlumbPrice AI — Deployment Guide

## Prerequisites

- Docker Engine 24+ and Docker Compose v2
- A Linux host (Ubuntu 22.04 LTS recommended) with at least 4 GB RAM and 20 GB disk
- An OpenAI API key with access to `gpt-4o`
- DNS pointed at the host (for TLS via Let's Encrypt in production)

---

## 1. Environment Variables

Copy the example files and fill in values before running any `docker compose` command.

```bash
cp api/.env.example api/.env
```

### Required Variables

| Variable                  | Description                                                  | Example                                   |
|---------------------------|--------------------------------------------------------------|-------------------------------------------|
| `DATABASE_URL`            | Async PostgreSQL DSN                                         | `postgresql+asyncpg://pp:secret@db/pp`    |
| `DATABASE_URL_SYNC`       | Sync DSN used by Alembic                                     | `postgresql+psycopg2://pp:secret@db/pp`   |
| `REDIS_URL`               | Celery broker URL                                            | `redis://redis:6379/0`                    |
| `CELERY_RESULT_BACKEND`   | Celery result backend URL                                    | `redis://redis:6379/1`                    |
| `SECRET_KEY`              | JWT signing secret (min 32 chars, random)                    | `openssl rand -hex 32`                    |
| `OPENAI_API_KEY`          | OpenAI API key                                               | `sk-proj-...`                             |
| `MINIO_ENDPOINT`          | MinIO host:port                                              | `minio:9000`                              |
| `MINIO_ACCESS_KEY`        | MinIO access key                                             | `minioadmin`                              |
| `MINIO_SECRET_KEY`        | MinIO secret key                                             | `minioadmin`                              |
| `MINIO_BUCKET`            | Default storage bucket name                                  | `plumbprice`                              |

### Optional Variables

| Variable                  | Default                   | Description                                          |
|---------------------------|---------------------------|------------------------------------------------------|
| `ENVIRONMENT`             | `development`             | `development` or `production`                        |
| `LOG_LEVEL`               | `INFO`                    | Structlog level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `ALLOWED_ORIGINS`         | `http://localhost:5173`   | Comma-separated CORS allowed origins                 |
| `ACCESS_TOKEN_EXPIRE_MINS`| `30`                      | JWT access token expiry in minutes                   |
| `REFRESH_TOKEN_EXPIRE_DAYS`| `7`                      | JWT refresh token expiry in days                     |
| `OPENAI_MODEL`            | `gpt-4o`                  | LLM model name                                       |
| `OPENAI_TEMPERATURE`      | `0.1`                     | LLM temperature (low = more deterministic)           |
| `DEFAULT_COUNTY`          | `tarrant`                 | Default county for tax calculations                  |
| `DEFAULT_SUPPLIER`        | `ferguson`                | Default preferred supplier slug                      |
| `RATE_LIMIT_PER_MIN`      | `30`                      | LLM endpoint rate limit per user per minute          |

---

## 2. Docker Compose — Development

```bash
# Start all services (db, redis, minio, api, worker, beat, web)
docker compose up -d

# Tail API logs
docker compose logs -f api

# Tail worker logs
docker compose logs -f worker
```

The development compose file mounts source directories as volumes for hot reload:
- API: `uvicorn --reload` watches `api/app/`
- Worker: `watchfiles` restarts on `worker/` changes

---

## 3. Docker Compose — Production

Create a `docker-compose.prod.yml` override file:

```yaml
services:
  api:
    image: plumbprice/api:latest
    restart: always
    environment:
      - ENVIRONMENT=production
      - LOG_LEVEL=WARNING
    deploy:
      replicas: 2

  worker:
    image: plumbprice/api:latest
    command: celery -A worker worker --loglevel=warning --concurrency=4
    restart: always

  beat:
    image: plumbprice/api:latest
    command: celery -A worker beat --loglevel=warning --scheduler celery.beat:PersistentScheduler
    restart: always

  web:
    image: plumbprice/web:latest
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /etc/letsencrypt:/etc/letsencrypt:ro
      - ./nginx/nginx.prod.conf:/etc/nginx/nginx.conf:ro

  db:
    restart: always
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}

  redis:
    restart: always

  minio:
    restart: always
    volumes:
      - miniodata:/data
```

Start production stack:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## 4. Building Images

```bash
# Build API and worker image
docker build -t plumbprice/api:latest ./api

# Build web image
docker build -t plumbprice/web:latest ./web

# Or use the compose build shortcut
docker compose build
```

Tag and push to a registry before deploying to a remote host:

```bash
docker tag plumbprice/api:latest registry.example.com/plumbprice/api:1.0.0
docker push registry.example.com/plumbprice/api:1.0.0
```

---

## 5. Database Migrations

Alembic manages all schema changes. Never edit the database schema by hand.

### Running Migrations

Migrations should be run before starting the API service. In a Docker Compose environment:

```bash
# Run migrations (one-time or on deploy)
docker compose run --rm api alembic upgrade head

# Or, if the API container is already running:
docker compose exec api alembic upgrade head
```

### Checking Migration Status

```bash
docker compose exec api alembic current
docker compose exec api alembic history --verbose
```

### Rolling Back

```bash
# Roll back one revision
docker compose exec api alembic downgrade -1

# Roll back to a specific revision
docker compose exec api alembic downgrade 001
```

### Creating a New Migration

After modifying SQLAlchemy models in `api/app/models/`:

```bash
# Auto-generate migration from model diff
docker compose exec api alembic revision --autogenerate -m "add_widget_table"

# Or create an empty migration for manual SQL
docker compose exec api alembic revision -m "add_custom_index"
```

Always review the auto-generated file in `api/alembic/versions/` before applying it. Auto-generate
does not detect column renames (it sees a drop + add), so handle renames manually.

---

## 6. Seeding the Database

The seed script populates suppliers, products, labor templates, material assemblies, and markup
rules. It is idempotent in spirit but not in implementation — run it only on a fresh database or
after a full `downgrade`/`upgrade` cycle.

```bash
# Run seed against the running DB container
docker compose exec api python scripts/seed_db.py
```

Expected output:

```
Seeding suppliers...
  + Ferguson Enterprises (id=1)
  + Moore Supply Co. (id=2)
  + Apex Supply (id=3)

Seeding 87 canonical items x 3 suppliers...
  + 261 supplier products

Seeding 32 labor templates...
  + 32 templates

Seeding 18 material assemblies...
  + 18 assemblies

Seeding markup rules...
  + 3 markup rules

Seed complete!
```

---

## 7. Creating the First Admin User

```bash
docker compose exec api python scripts/create_admin.py admin@acmeplumbing.com "Str0ng!Pass" "Admin User"
```

The admin user can then log in via the web UI and create additional users.

---

## 8. Celery Beat Scheduler

The Beat service triggers the daily supplier refresh task. Verify it is running:

```bash
docker compose logs beat
```

Expected log line (every 24 hours):

```
Scheduler: Sending due task refresh-supplier-prices-daily (tasks.supplier_refresh.refresh_all_suppliers)
```

To trigger the refresh manually without waiting for the schedule:

```bash
# From inside the worker container
docker compose exec worker celery -A worker call tasks.supplier_refresh.refresh_all_suppliers

# Or via the admin API endpoint
curl -X POST http://localhost:8000/api/v1/admin/worker/trigger-refresh \
  -H "Authorization: Bearer <admin_token>"
```

---

## 9. MinIO Setup

After the MinIO container starts, create the default bucket. MinIO will not create it automatically.

```bash
# Install mc (MinIO client) inside the container
docker compose exec minio mc alias set local http://localhost:9000 minioadmin minioadmin
docker compose exec minio mc mb local/plumbprice
docker compose exec minio mc anonymous set download local/plumbprice/exports
```

Access the MinIO console at `http://localhost:9001` (credentials: `minioadmin` / `minioadmin`).

In production, change the `MINIO_ACCESS_KEY` and `MINIO_SECRET_KEY` to strong random values and
restrict the console port to the private network.

---

## 10. Health Checks

The API exposes two health endpoints used by load balancers and container orchestrators:

```bash
# Liveness — is the process alive?
curl http://localhost:8000/health
# {"status": "ok"}

# Readiness — can it serve traffic? (checks DB + Redis)
curl http://localhost:8000/health/ready
# {"status": "ready", "db": "ok", "redis": "ok"}
```

Docker Compose health check configuration (in `docker-compose.yml`):

```yaml
api:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 20s
```

---

## 11. Log Management

All services use structured JSON logging via `structlog`. In production, pipe logs to a
centralized system (Loki, CloudWatch, Datadog):

```bash
# View structured logs
docker compose logs -f api | jq '.'

# Filter for errors only
docker compose logs -f api | jq 'select(.level == "error")'
```

---

## 12. Deployment Checklist

Use this checklist for every production deployment:

- [ ] Pull latest images or rebuild: `docker compose build`
- [ ] Verify `.env` has no placeholder values
- [ ] Verify `SECRET_KEY` is at least 32 random characters
- [ ] Run database migrations: `docker compose run --rm api alembic upgrade head`
- [ ] Verify migration status: `docker compose exec api alembic current`
- [ ] Start services: `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`
- [ ] Check API health: `curl https://api.plumbprice.com/health/ready`
- [ ] Check Beat scheduler is running: `docker compose logs beat | tail -20`
- [ ] Check worker is consuming tasks: `docker compose logs worker | tail -20`
- [ ] Create admin user if first deploy: `docker compose exec api python scripts/create_admin.py ...`
- [ ] Seed database if first deploy: `docker compose exec api python scripts/seed_db.py`
- [ ] Verify MinIO bucket exists and is accessible
- [ ] Test a chat/price request end-to-end via the web UI

---

## 13. Updating Supplier Prices

Phase 1 prices are seeded manually. To update a product's cost outside the automated refresh:

```bash
# Via the admin API
curl -X PATCH http://localhost:8000/api/v1/admin/suppliers/1/products/204 \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"cost": 192.50, "confidence_score": 1.0}'
```

This automatically appends a row to `supplier_price_history` for audit purposes and resets the
`last_verified` timestamp.

---

## 14. Backup and Restore

### PostgreSQL Backup

```bash
# Dump to file
docker compose exec db pg_dump -U pp pp > backup-$(date +%Y%m%d).sql

# Restore
docker compose exec -T db psql -U pp pp < backup-20250615.sql
```

### MinIO Backup

Use `mc mirror` to sync the MinIO bucket to an external S3 bucket:

```bash
docker compose exec minio mc alias set s3remote s3://s3.amazonaws.com AWS_KEY AWS_SECRET
docker compose exec minio mc mirror local/plumbprice s3remote/plumbprice-backup
```

Schedule nightly with cron on the host:

```
0 2 * * * docker compose -f /opt/plumbprice/docker-compose.yml exec -T minio mc mirror local/plumbprice s3remote/plumbprice-backup >> /var/log/plumbprice-backup.log 2>&1
```
