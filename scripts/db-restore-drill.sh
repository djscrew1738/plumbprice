#!/usr/bin/env bash
# PlumbPrice restore drill (b5).
#
# Pulls the most recent dump from MinIO and restores it into a temporary
# database, then runs a smoke query. Use this in CI weekly to prove
# backups actually work — the only true backup is a tested backup.
#
# Required env: DATABASE_URL (with admin privs to create/drop a temp DB),
#   MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_BACKUP_BUCKET.

set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL is required (admin-capable)}"
: "${MINIO_ENDPOINT:?MINIO_ENDPOINT is required}"
: "${MINIO_ACCESS_KEY:?MINIO_ACCESS_KEY is required}"
: "${MINIO_SECRET_KEY:?MINIO_SECRET_KEY is required}"
: "${MINIO_BACKUP_BUCKET:=backups}"

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

mc alias set pprestore "$MINIO_ENDPOINT" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" >/dev/null

LATEST=$(mc find "pprestore/$MINIO_BACKUP_BUCKET/postgres/" --name "*.sql.gz" \
    | sort | tail -n1 || true)
if [[ -z "$LATEST" ]]; then
    echo "!! no dumps found under $MINIO_BACKUP_BUCKET/postgres/" >&2
    exit 1
fi
echo ">> latest dump: $LATEST"

DUMP_FILE="$TMP/$(basename "$LATEST")"
mc cp "$LATEST" "$DUMP_FILE"

# Build a connection string for a fresh, ephemeral DB on the same server.
DB_URL_BASE="${DATABASE_URL%/*}"   # strip last path segment (db name)
TEST_DB="restore_drill_$(date -u +%s)"

echo ">> creating test DB: $TEST_DB"
psql "$DATABASE_URL" -c "CREATE DATABASE \"$TEST_DB\";"

echo ">> restoring..."
gunzip -c "$DUMP_FILE" | psql "$DB_URL_BASE/$TEST_DB"

echo ">> smoke check..."
psql "$DB_URL_BASE/$TEST_DB" -c "SELECT count(*) AS users FROM users;" || {
    echo "!! smoke query failed" >&2
    psql "$DATABASE_URL" -c "DROP DATABASE \"$TEST_DB\";" || true
    exit 3
}

echo ">> dropping test DB"
psql "$DATABASE_URL" -c "DROP DATABASE \"$TEST_DB\";"

echo ">> drill passed."
