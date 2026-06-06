#!/usr/bin/env bash
# Deploy PlumbPrice AI v3.0.0 to production
# Run this on the production server (app.ctlplumbingllc.com)
#
# Prerequisites:
#   - SSH access to production server
#   - .env and deploy/runtime.env are configured
#   - Docker Compose v2 is installed
#   - nginx is configured (deploy/nginx-ctlplumbingllc.conf)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> PlumbPrice AI v3.0.0 Production Deploy"
echo ""

# 1. Pull latest code
echo "==> Pulling latest code"
git pull origin main || git pull origin master || { echo "Failed to pull"; exit 1; }

# 2. Run database migrations (v3.0.0 adds 5 new tables + columns)
echo "==> Running database migrations"
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T api alembic upgrade head

# 3. Build and restart the full stack
echo "==> Building and restarting Docker Compose stack"
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# 4. Wait for services to be healthy
echo "==> Waiting for services to be healthy..."
for i in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:8201/health" > /dev/null 2>&1; then
    echo "    API is healthy after ${i}s"
    break
  fi
  sleep 1
  if [ "$i" -eq 30 ]; then
    echo "ERROR: API health check failed after 30s"
    docker compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail=20 api
    exit 1
  fi
done

for i in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:3201" > /dev/null 2>&1; then
    echo "    Web is healthy after ${i}s"
    break
  fi
  sleep 1
  if [ "$i" -eq 30 ]; then
    echo "ERROR: Web health check failed after 30s"
    docker compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail=20 web
    exit 1
  fi
done

# 5. Purge Cloudflare cache (optional but recommended)
echo "==> Purging Cloudflare cache"
if [ -f "$REPO_ROOT/scripts/purge-cloudflare-cache.sh" ]; then
  bash "$REPO_ROOT/scripts/purge-cloudflare-cache.sh" || echo "    WARNING: Cloudflare purge failed (non-fatal)"
else
  echo "    WARNING: purge-cloudflare-cache.sh not found, skipping"
fi

# 6. Verify v3 API is responding
echo "==> Verifying v3 API"
curl -sf "http://127.0.0.1:8201/api/v3/chat/price" -X OPTIONS > /dev/null 2>&1 || true
echo "    v3 API reachable"

# 7. Show running containers
echo ""
echo "==> Deploy complete! Running containers:"
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps

echo ""
echo "Site: https://app.ctlplumbingllc.com"
echo "Version: v3.0.0"
