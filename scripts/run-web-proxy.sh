#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/djscrew/projects/web/plumbprice-ai"
ENV_FILE="$ROOT/deploy/runtime.env"

set -a
source "$ENV_FILE"
set +a

exec env \
  WEB_PORT="${WEB_PORT}" \
  NEXT_INTERNAL_PORT="${NEXT_INTERNAL_PORT}" \
  API_PORT="${API_PORT}" \
  node "$ROOT/scripts/web-proxy.js"
