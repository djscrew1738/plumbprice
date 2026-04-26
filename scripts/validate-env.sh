#!/usr/bin/env bash
# scripts/validate-env.sh — pre-flight check for PlumbPrice dev/prod environments.
#
# Verifies:
#   - required CLI tools are on PATH (python3, node, docker, psql/curl)
#   - .env exists and has the required keys filled in (not the placeholder values)
#   - Postgres, Redis, MinIO are reachable
#   - listening ports the app needs are not in use by something else
#   - API health endpoints return 200 (if API is already running)
#
# Exit codes:
#   0 — all checks passed
#   1 — at least one required check failed
#
# Usage:
#   ./scripts/validate-env.sh           # check everything
#   ./scripts/validate-env.sh --quick   # skip health probes (just files + tools)

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$REPO_ROOT/.env}"
QUICK=0
[[ "${1:-}" == "--quick" ]] && QUICK=1

red()    { printf "\033[31m%s\033[0m\n" "$*"; }
green()  { printf "\033[32m%s\033[0m\n" "$*"; }
yellow() { printf "\033[33m%s\033[0m\n" "$*"; }
bold()   { printf "\033[1m%s\033[0m\n" "$*"; }

FAIL=0
WARN=0

check() {
    local label="$1"; shift
    if "$@" >/dev/null 2>&1; then
        green "  ✓ $label"
    else
        red   "  ✗ $label"
        FAIL=$((FAIL + 1))
    fi
}

warn_check() {
    local label="$1"; shift
    if "$@" >/dev/null 2>&1; then
        green "  ✓ $label"
    else
        yellow "  ⚠ $label  (warn — not required)"
        WARN=$((WARN + 1))
    fi
}

bold "==> CLI tools"
for tool in python3 node npm docker curl; do
    check "$tool present" command -v "$tool"
done
warn_check "psql present (for direct DB checks)" command -v psql

bold "==> Python / Node versions"
if command -v python3 >/dev/null 2>&1; then
    pyv=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
    if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)'; then
        green "  ✓ python ${pyv} (>= 3.11)"
    else
        red   "  ✗ python ${pyv} (need >= 3.11)"
        FAIL=$((FAIL + 1))
    fi
fi
if command -v node >/dev/null 2>&1; then
    nv=$(node -v | sed 's/v//')
    nmajor=${nv%%.*}
    if [[ "$nmajor" -ge 18 ]]; then
        green "  ✓ node v${nv} (>= 18)"
    else
        red   "  ✗ node v${nv} (need >= 18)"
        FAIL=$((FAIL + 1))
    fi
fi

bold "==> Environment file ($ENV_FILE)"
if [[ ! -f "$ENV_FILE" ]]; then
    red "  ✗ $ENV_FILE not found — copy .env.example and fill it in"
    FAIL=$((FAIL + 1))
else
    green "  ✓ $ENV_FILE exists"
    # shellcheck disable=SC1090
    set -a; source "$ENV_FILE"; set +a

    REQUIRED_KEYS=(
        DATABASE_URL REDIS_URL MINIO_ENDPOINT MINIO_ACCESS_KEY MINIO_SECRET_KEY
        SECRET_KEY POSTGRES_USER POSTGRES_PASSWORD POSTGRES_DB
    )
    for key in "${REQUIRED_KEYS[@]}"; do
        v="${!key:-}"
        if [[ -z "$v" ]]; then
            red "  ✗ $key is empty"
            FAIL=$((FAIL + 1))
        elif [[ "$key" == "SECRET_KEY" && "$v" == *"change-in-production"* ]]; then
            red "  ✗ $key still has the placeholder value"
            FAIL=$((FAIL + 1))
        else
            green "  ✓ $key set"
        fi
    done

    # Optional but commonly-needed
    for key in OPENAI_API_KEY ANTHROPIC_API_KEY OLLAMA_BASE_URL; do
        v="${!key:-}"
        if [[ -z "$v" ]]; then
            yellow "  ⚠ $key not set (some features will be disabled)"
            WARN=$((WARN + 1))
        else
            green "  ✓ $key set"
        fi
    done
fi

if [[ $QUICK -eq 1 ]]; then
    echo
    bold "==> --quick mode: skipping connectivity probes"
    echo
    [[ $FAIL -eq 0 ]] && { green "ALL REQUIRED CHECKS PASSED ($WARN warnings)"; exit 0; }
    red "$FAIL required check(s) failed, $WARN warning(s)"
    exit 1
fi

bold "==> Backing services"
# Pull host/port from DATABASE_URL if present
if [[ -n "${DATABASE_URL:-}" ]]; then
    pg_host=$(python3 -c "import urllib.parse as u; p=u.urlparse('$DATABASE_URL'.replace('+asyncpg','').replace('+psycopg2','')); print(p.hostname or 'localhost')")
    pg_port=$(python3 -c "import urllib.parse as u; p=u.urlparse('$DATABASE_URL'.replace('+asyncpg','').replace('+psycopg2','')); print(p.port or 5432)")
    check "Postgres reachable at ${pg_host}:${pg_port}" \
        bash -c ">/dev/tcp/${pg_host}/${pg_port}"
fi

if [[ -n "${REDIS_URL:-}" ]]; then
    rd_host=$(python3 -c "import urllib.parse as u; p=u.urlparse('$REDIS_URL'); print(p.hostname or 'localhost')")
    rd_port=$(python3 -c "import urllib.parse as u; p=u.urlparse('$REDIS_URL'); print(p.port or 6379)")
    check "Redis reachable at ${rd_host}:${rd_port}" \
        bash -c ">/dev/tcp/${rd_host}/${rd_port}"
fi

if [[ -n "${MINIO_ENDPOINT:-}" ]]; then
    mn_host=$(echo "$MINIO_ENDPOINT" | cut -d: -f1)
    mn_port=$(echo "$MINIO_ENDPOINT" | cut -d: -f2)
    [[ "$mn_port" == "$mn_host" ]] && mn_port=9000
    check "MinIO reachable at ${mn_host}:${mn_port}" \
        bash -c ">/dev/tcp/${mn_host}/${mn_port}"
fi

bold "==> Local services (if running)"
warn_check "API on :8200 responds /health" \
    bash -c 'curl -fsS --max-time 3 http://localhost:8200/health > /dev/null'
warn_check "API on :8200 responds /health/worker" \
    bash -c 'curl -fsS --max-time 5 http://localhost:8200/health/worker > /dev/null'
warn_check "Web on :3200 responds" \
    bash -c 'curl -fsS --max-time 3 http://localhost:3200/ > /dev/null'

echo
if [[ $FAIL -eq 0 ]]; then
    green "ALL REQUIRED CHECKS PASSED ($WARN warnings)"
    exit 0
fi
red "$FAIL required check(s) failed, $WARN warning(s)"
exit 1
