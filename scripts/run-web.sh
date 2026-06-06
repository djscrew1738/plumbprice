#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$ROOT/deploy/runtime.env"
BUILD_DIR="$ROOT/web/.next"
# Next.js standalone output mirrors the absolute path; find the actual server.js.
STANDALONE_SERVER="$BUILD_DIR/standalone/server.js"
if [[ ! -f "$STANDALONE_SERVER" ]]; then
  STANDALONE_SERVER="$(find "$BUILD_DIR/standalone" -name "server.js" -not -path "*/node_modules/*" | head -1)"
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing runtime env at $ENV_FILE" >&2
  echo "Copy deploy/runtime.env.example to deploy/runtime.env and fill in production values." >&2
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

if [[ ! -f "$STANDALONE_SERVER" ]]; then
  echo "Missing standalone frontend build at $STANDALONE_SERVER" >&2
  exit 1
fi

# Patch any stale API proxy URLs in the build artifacts (catches localhost:*, 127.0.0.1:*)
PATCH_FILES=(
  "$BUILD_DIR/routes-manifest.json"
  "$BUILD_DIR/required-server-files.json"
  "$STANDALONE_SERVER"
  "$BUILD_DIR/standalone/.next/routes-manifest.json"
  "$BUILD_DIR/standalone/.next/required-server-files.json"
)
for f in "${PATCH_FILES[@]}"; do
  [[ -f "$f" ]] || continue
  perl -0pi -e "
    s|http://localhost:\d+/api/|${API_URL}/api/|g;
    s|http://127\.0\.0\.1:\d+/api/|${API_URL}/api/|g;
    s|http://${PUBLIC_HOST:-NOPUBHOST}:\d+/api/|${API_URL}/api/|g;
    s|https://${PUBLIC_HOST:-NOPUBHOST}/api/|${API_URL}/api/|g;
  " "$f"
done

cd "$(dirname "$STANDALONE_SERVER")"
exec env PORT="${WEB_PORT}" HOSTNAME=0.0.0.0 node "$STANDALONE_SERVER"
