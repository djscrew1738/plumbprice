#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$ROOT/deploy/runtime.env"
BUILD_DIR="$ROOT/web/.next"
STANDALONE_SERVER="$BUILD_DIR/standalone/server.js"

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

perl -0pi -e "s|http://localhost:8000/api/:path\\*|${API_URL}/api/:path*|g; s|http://${PUBLIC_HOST}:8200/api/:path\\*|${API_URL}/api/:path*|g; s|http://${PUBLIC_HOST}:${API_PORT}/api/:path\\*|${API_URL}/api/:path*|g; s|https://${PUBLIC_HOST}/api/:path\\*|${API_URL}/api/:path*|g" \
  "$BUILD_DIR/routes-manifest.json" \
  "$BUILD_DIR/required-server-files.json" \
  "$STANDALONE_SERVER"

cd "$ROOT/web"
exec env PORT="${WEB_PORT}" HOSTNAME=0.0.0.0 node "$STANDALONE_SERVER"
