#!/usr/bin/env bash
# Deploy Next.js web app:
#   build → retain multiple static generations → restart service → purge Cloudflare cache
#   → validate live login chunk availability for browser UAs
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
STATIC_DIR="$STANDALONE_DIR/.next/static"
RELEASES_DIR="$STANDALONE_DIR/.next/static_releases"
RELEASE_ID="$(date -u +%Y%m%dT%H%M%SZ)"

TARGET_URL="${TARGET_URL:-https://pricing.ctlplumbingllc.com}"
HEALTHCHECK_PATH="${HEALTHCHECK_PATH:-/}"
VALIDATE_PATH="${VALIDATE_PATH:-/login}"
RETAIN_STATIC_GENERATIONS="${RETAIN_STATIC_GENERATIONS:-5}"
REQUIRE_CF_PURGE="${REQUIRE_CF_PURGE:-0}"

BROWSER_UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'
HEADLESS_UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/147.0.7727.15 Safari/537.36'

is_positive_integer() {
  [[ "$1" =~ ^[1-9][0-9]*$ ]]
}

has_cf_credentials() {
  [ -n "${CF_API_TOKEN:-}" ] || { [ -n "${CF_EMAIL:-}" ] && [ -n "${CF_API_KEY:-}" ]; }
}

validate_chunks_for_ua() {
  local label="$1"
  local ua="$2"
  local login_url="${TARGET_URL%/}${VALIDATE_PATH}"
  local html
  local chunk_paths=()
  local failed=0

  echo "==> Validating chunk availability ($label)"
  html="$(curl -fsSL -A "$ua" "$login_url")"
  mapfile -t chunk_paths < <(printf '%s' "$html" | grep -oE '/_next/static[^" ]+\.js' | sort -u)

  if [ "${#chunk_paths[@]}" -eq 0 ]; then
    echo "ERROR: No chunk URLs found in $login_url for $label"
    exit 1
  fi

  for path in "${chunk_paths[@]}"; do
    local code
    code="$(curl -s -o /dev/null -w '%{http_code}' -A "$ua" "${TARGET_URL%/}${path}")"
    if [ "$code" != "200" ]; then
      echo "    FAIL [$code] ${path}"
      failed=1
    fi
  done

  if [ "$failed" -ne 0 ]; then
    echo "ERROR: Chunk validation failed for $label"
    exit 1
  fi

  echo "    OK: ${#chunk_paths[@]} chunk files accessible for $label"
}

if ! is_positive_integer "$RETAIN_STATIC_GENERATIONS"; then
  echo "ERROR: RETAIN_STATIC_GENERATIONS must be a positive integer (got: $RETAIN_STATIC_GENERATIONS)"
  exit 1
fi

cd "$REPO_ROOT"
mkdir -p "$RELEASES_DIR"

if [ -d "$STATIC_DIR" ] && [ -z "$(find "$RELEASES_DIR" -mindepth 1 -maxdepth 1 -type d | head -n 1)" ]; then
  LEGACY_RELEASE="$RELEASES_DIR/legacy-$(date -u +%Y%m%dT%H%M%SZ)"
  echo "==> Bootstrapping release archive from currently deployed static assets"
  mkdir -p "$LEGACY_RELEASE"
  cp -a "$STATIC_DIR/." "$LEGACY_RELEASE/"
fi

echo "==> Building Next.js (production)"
cd "$WEB_DIR"
npm run build

echo "==> Copying public/ to standalone"
rm -rf "$STANDALONE_DIR/public"
cp -r "$WEB_DIR/public" "$STANDALONE_DIR/public"

echo "==> Staging static assets for release $RELEASE_ID"
NEW_RELEASE_DIR="$RELEASES_DIR/$RELEASE_ID"
rm -rf "$NEW_RELEASE_DIR"
mkdir -p "$NEW_RELEASE_DIR"
cp -a "$WEB_DIR/.next/static/." "$NEW_RELEASE_DIR/"

echo "==> Rebuilding standalone static directory from last $RETAIN_STATIC_GENERATIONS generation(s)"
rm -rf "$STATIC_DIR"
mkdir -p "$STATIC_DIR"

mapfile -t release_dirs < <(find "$RELEASES_DIR" -mindepth 1 -maxdepth 1 -type d | sort -r)
declare -A keep_dirs=()
kept_count=0
for dir in "${release_dirs[@]}"; do
  if [ "$kept_count" -ge "$RETAIN_STATIC_GENERATIONS" ]; then
    break
  fi
  cp -a "$dir/." "$STATIC_DIR/"
  keep_dirs["$dir"]=1
  kept_count=$((kept_count + 1))
done

for dir in "${release_dirs[@]}"; do
  if [ -z "${keep_dirs[$dir]:-}" ]; then
    rm -rf "$dir"
  fi
done

echo "==> Restarting plumbprice-web service"
sudo systemctl restart plumbprice-web

echo "==> Waiting for service to start..."
for i in $(seq 1 30); do
  if curl -sf "http://localhost:3200${HEALTHCHECK_PATH}" > /dev/null 2>&1; then
    echo "    Service is up after ${i}s"
    break
  fi
  sleep 1
  if [ "$i" -eq 30 ]; then
    echo "ERROR: Service did not come up after 30s"
    systemctl status plumbprice-web --no-pager | tail -10
    exit 1
  fi
done

echo "==> Purging Cloudflare cache"
if has_cf_credentials; then
  bash "$REPO_ROOT/scripts/purge-cloudflare-cache.sh"
else
  if [ "$REQUIRE_CF_PURGE" = "1" ]; then
    echo "ERROR: Cloudflare credentials missing and REQUIRE_CF_PURGE=1"
    echo "Set CF_API_TOKEN (recommended), or CF_EMAIL + CF_API_KEY."
    echo "To bypass temporarily (not recommended): REQUIRE_CF_PURGE=0 ./scripts/deploy-web.sh"
    exit 1
  fi
  echo "    WARNING: skipping Cloudflare purge because credentials are missing"
fi

validate_chunks_for_ua "browser UA" "$BROWSER_UA"
validate_chunks_for_ua "headless UA" "$HEADLESS_UA"

echo ""
echo "==> Deploy complete! Site: ${TARGET_URL%/}"
