#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$ROOT/deploy/runtime.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing runtime env at $ENV_FILE" >&2
  echo "Copy deploy/runtime.env.example to deploy/runtime.env and fill in production values." >&2
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

cd "$ROOT/api"
exec "$ROOT/api/.venv/bin/python" -m uvicorn app.main:app --host 0.0.0.0 --port "${API_PORT}"
