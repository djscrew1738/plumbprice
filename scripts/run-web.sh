#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/djscrew/projects/web/plumbprice-ai"
ENV_FILE="$ROOT/deploy/runtime.env"
BUILD_DIR="$ROOT/web/.next"
STANDALONE_SERVER="$BUILD_DIR/standalone/server.js"

set -a
source "$ENV_FILE"
set +a

if [[ ! -f "$STANDALONE_SERVER" ]]; then
  echo "Missing standalone frontend build at $STANDALONE_SERVER" >&2
  exit 1
fi

perl -0pi -e "s|http://localhost:8000/api/:path\\*|${API_URL}/api/:path*|g; s|http://${PUBLIC_HOST}:8200/api/:path\\*|${API_URL}/api/:path*|g" \
  "$BUILD_DIR/routes-manifest.json" \
  "$BUILD_DIR/required-server-files.json" \
  "$STANDALONE_SERVER"

cd "$ROOT/web"
exec env PORT="${WEB_PORT}" HOSTNAME=0.0.0.0 node "$STANDALONE_SERVER"
