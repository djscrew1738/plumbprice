#!/usr/bin/env bash
# PlumbPrice nightly Postgres backup (b5).
#
# Streams pg_dump of the configured database to MinIO under the
# bucket/prefix specified by env vars. Designed to run from cron or
# a CI scheduled job. Idempotent — re-running on the same day overwrites
# the day's archive.
#
# Required env:
#   DATABASE_URL          postgres connection string (libpq form)
#   MINIO_ENDPOINT        e.g. http://minio:9000
#   MINIO_ACCESS_KEY
#   MINIO_SECRET_KEY
#   MINIO_BACKUP_BUCKET   bucket name, default: backups
#
# Optional:
#   RETENTION_DAYS        default 30
#
# This script does not embed credentials. Configure them via the host's
# secrets manager.

set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL is required}"
: "${MINIO_ENDPOINT:?MINIO_ENDPOINT is required}"
: "${MINIO_ACCESS_KEY:?MINIO_ACCESS_KEY is required}"
: "${MINIO_SECRET_KEY:?MINIO_SECRET_KEY is required}"
: "${MINIO_BACKUP_BUCKET:=backups}"
: "${RETENTION_DAYS:=30}"

STAMP=$(date -u +%Y%m%d-%H%M%S)
DATE_DIR=$(date -u +%Y/%m/%d)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
DUMP_FILE="$TMP/plumbprice-$STAMP.sql.gz"

echo ">> dumping postgres → $DUMP_FILE"
pg_dump --format=plain --no-owner --no-privileges "$DATABASE_URL" | gzip -9 > "$DUMP_FILE"

if ! command -v mc >/dev/null 2>&1; then
  echo "!! 'mc' (minio client) not found — install from https://min.io/docs/minio/linux/reference/minio-mc.html" >&2
  exit 2
fi

mc alias set ppbackup "$MINIO_ENDPOINT" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" >/dev/null

# Ensure bucket exists (idempotent).
mc mb --ignore-existing "ppbackup/$MINIO_BACKUP_BUCKET" >/dev/null

DEST="ppbackup/$MINIO_BACKUP_BUCKET/postgres/$DATE_DIR/$(basename "$DUMP_FILE")"
echo ">> uploading → $DEST"
mc cp "$DUMP_FILE" "$DEST"

echo ">> pruning archives older than $RETENTION_DAYS days"
mc rm --recursive --force \
    --older-than "${RETENTION_DAYS}d" \
    "ppbackup/$MINIO_BACKUP_BUCKET/postgres/" || true

echo ">> done."
