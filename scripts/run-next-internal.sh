#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$ROOT/deploy/runtime.env"
STANDALONE_SERVER="$ROOT/web/.next/standalone/server.js"

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

cd "$ROOT/web"
exec env PORT="${NEXT_INTERNAL_PORT}" HOSTNAME=127.0.0.1 node "$STANDALONE_SERVER"
