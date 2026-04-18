#!/usr/bin/env bash
# Deploy Next.js web app:
#   build → merge static assets into standalone → restart service → purge Cloudflare cache
#
# Usage:
#   ./scripts/deploy-web.sh
#   CF_API_TOKEN=xxx ./scripts/deploy-web.sh   # also purges Cloudflare cache
#
# Requires: sudo access (for systemctl restart plumbprice-web)
#
# NOTE: Static assets are MERGED (not replaced) to preserve old chunk files.
# Cloudflare edge may serve cached HTML referencing old chunk hashes;
# keeping old chunks on disk prevents 404 errors until cache is purged.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_DIR="$REPO_ROOT/web"
STANDALONE_DIR="$WEB_DIR/.next/standalone"

cd "$REPO_ROOT"

echo "==> Building Next.js (production)"
cd "$WEB_DIR"
npm run build

echo "==> Copying public/ to standalone"
rm -rf "$STANDALONE_DIR/public"
cp -r "$WEB_DIR/public" "$STANDALONE_DIR/public"

echo "==> Merging .next/static into standalone (preserving old chunks)"
mkdir -p "$STANDALONE_DIR/.next/static"
cp -r "$WEB_DIR/.next/static/"* "$STANDALONE_DIR/.next/static/"

echo "==> Restarting plumbprice-web service"
sudo systemctl restart plumbprice-web

echo "==> Waiting for service to start..."
for i in $(seq 1 20); do
  if curl -sf "http://localhost:3200/" > /dev/null 2>&1; then
    echo "    Service is up after ${i}s"
    break
  fi
  sleep 1
  if [ "$i" -eq 20 ]; then
    echo "ERROR: Service did not come up after 20s"
    systemctl status plumbprice-web --no-pager | tail -10
    exit 1
  fi
done

echo "==> Purging Cloudflare cache"
if [ -n "${CF_API_TOKEN:-}" ]; then
  bash "$REPO_ROOT/scripts/purge-cloudflare-cache.sh"
else
  echo "    WARNING: CF_API_TOKEN not set — skipping cache purge"
  echo "    Run manually: CF_API_TOKEN=xxx ./scripts/purge-cloudflare-cache.sh"
  echo "    Or purge from: https://dash.cloudflare.com → ctlplumbingllc.com → Caching → Purge Everything"
fi

echo ""
echo "==> Deploy complete! Site: https://pricing.ctlplumbingllc.com"
