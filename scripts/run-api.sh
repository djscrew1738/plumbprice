#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/djscrew/projects/web/plumbprice-ai"
ENV_FILE="$ROOT/deploy/runtime.env"

set -a
source "$ENV_FILE"
set +a

cd "$ROOT/api"
exec "$ROOT/api/.venv/bin/python" -m uvicorn app.main:app --host 0.0.0.0 --port "${API_PORT}"
