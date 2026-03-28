#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/djscrew/projects/web/plumbprice-ai"
ENV_FILE="$ROOT/deploy/runtime.env"
STANDALONE_SERVER="$ROOT/web/.next/standalone/server.js"

set -a
source "$ENV_FILE"
set +a

if [[ ! -f "$STANDALONE_SERVER" ]]; then
  echo "Missing standalone frontend build at $STANDALONE_SERVER" >&2
  exit 1
fi

cd "$ROOT/web"
exec env PORT="${NEXT_INTERNAL_PORT}" HOSTNAME=127.0.0.1 node "$STANDALONE_SERVER"
