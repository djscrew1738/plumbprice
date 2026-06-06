#!/usr/bin/env bash
# Deploy PlumbPrice AI v4.1.0 to production
# Run this on the production server (app.ctlplumbingllc.com)
#
# Prerequisites:
#   - SSH access to production server
#   - .env and deploy/runtime.env are configured
#   - Docker Compose v2 is installed
#   - nginx is configured (deploy/nginx-ctlplumbingllc.conf)
#
# New in v4.1.0:
#   - worker-ml service (ML fine-tuning queue)
#   - v4.1 migration (9 new tables/columns + HNSW pgvector index)
#   - Prometheus /metrics endpoint
#   - beautifulsoup4 + prometheus-fastapi-instrumentator in requirements.txt
#
# Optional new .env vars (safe to omit — features degrade gracefully):
#   FERGUSON_CLIENT_ID / FERGUSON_CLIENT_SECRET  (OAuth2 supplier pricing)
#   VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY / VAPID_SUBSCRIBER_EMAIL  (Web Push)
#   ML_FINETUNE_ENABLED=true  (default false — enable only when data ready)
#   MOORE_SUPPLY_ENABLED=true  (default false — simulation mode)
#   APEX_SUPPLY_ENABLED=true   (default false — simulation mode)
#   VISION_PROVIDER=openai     (default ollama — GPT-4V costs extra)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> PlumbPrice AI v4.1.0 Production Deploy"
echo ""

# 1. Pull latest code
echo "==> Pulling latest code from main"
git pull origin main || { echo "Failed to pull"; exit 1; }

# 2. Run database migrations
echo "==> Running database migrations (v4.1.0 — 9 new tables/columns + HNSW index)"
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T api alembic upgrade head

# 3. Build and restart the full stack (including new worker-ml service)
echo "==> Building and restarting Docker Compose stack (including worker-ml)"
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# 4. Wait for API health
echo "==> Waiting for API health..."
for i in $(seq 1 40); do
  if curl -sf "http://127.0.0.1:${API_PORT:-8201}/health" > /dev/null 2>&1; then
    echo "    API healthy after ${i}s"
    break
  fi
  sleep 1
  if [ "$i" -eq 40 ]; then
    echo "ERROR: API health check failed after 40s"
    docker compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail=30 api
    exit 1
  fi
done

# 5. Wait for Web health
echo "==> Waiting for Web health..."
for i in $(seq 1 40); do
  if curl -sf "http://127.0.0.1:${WEB_PORT:-3201}" > /dev/null 2>&1; then
    echo "    Web healthy after ${i}s"
    break
  fi
  sleep 1
  if [ "$i" -eq 40 ]; then
    echo "ERROR: Web health check failed after 40s"
    docker compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail=30 web
    exit 1
  fi
done

# 6. Verify v4.1 API routes
echo "==> Verifying v4.1 API endpoints"
curl -sf "http://127.0.0.1:${API_PORT:-8201}/api/v3/geo/county?lat=32.78&lng=-96.80" > /dev/null 2>&1 \
  && echo "    /api/v3/geo/county OK" || echo "    WARNING: geo endpoint not yet responding (non-fatal)"
curl -sf "http://127.0.0.1:${API_PORT:-8201}/metrics" > /dev/null 2>&1 \
  && echo "    /metrics (Prometheus) OK" || echo "    INFO: /metrics not enabled (prometheus-fastapi-instrumentator not installed)"

# 7. Purge Cloudflare cache
echo "==> Purging Cloudflare cache"
if [ -f "$REPO_ROOT/scripts/purge-cloudflare-cache.sh" ]; then
  bash "$REPO_ROOT/scripts/purge-cloudflare-cache.sh" || echo "    WARNING: Cloudflare purge failed (non-fatal)"
else
  echo "    WARNING: purge-cloudflare-cache.sh not found, skipping"
fi

# 8. Show running containers
echo ""
echo "==> Deploy complete! Running containers:"
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps

echo ""
echo "Site:    https://app.ctlplumbingllc.com"
echo "Version: v4.1.0"
echo ""
echo "New routes to verify:"
echo "  /field          — Field tech mobile home"
echo "  /field/photo    — Multi-photo job capture"
echo "  /field/voice    — Voice quote"
echo "  /admin/variance — Variance analytics"
echo "  /admin/models   — ML model registry"
