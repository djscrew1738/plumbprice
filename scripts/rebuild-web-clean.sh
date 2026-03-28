#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/djscrew/projects/web/plumbprice-ai"
WEB_DIR="$ROOT/web"
ARCHIVE_DIR="$ROOT/.build-artifacts"

mkdir -p "$ARCHIVE_DIR"

timestamp="$(date +%s)"

if [[ -d "$WEB_DIR/node_modules" ]]; then
  mv "$WEB_DIR/node_modules" "$ARCHIVE_DIR/node_modules.$timestamp"
fi

if [[ -d "$WEB_DIR/.next" ]]; then
  mv "$WEB_DIR/.next" "$ARCHIVE_DIR/.next.$timestamp"
fi

cd "$WEB_DIR"
npm ci
npm run build:prod
