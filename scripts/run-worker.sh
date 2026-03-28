#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/djscrew/projects/web/plumbprice-ai"
ENV_FILE="$ROOT/deploy/runtime.env"

set -a
source "$ENV_FILE"
set +a

cd "$ROOT/worker"
exec "$ROOT/api/.venv/bin/celery" -A worker.app worker --loglevel="${LOG_LEVEL}" --pool=solo
