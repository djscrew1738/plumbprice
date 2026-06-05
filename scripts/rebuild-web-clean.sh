#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
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

# Copy static assets into standalone (required for Next.js standalone deployment)
echo "Copying static assets to standalone..."
cp -r .next/static .next/standalone/.next/static
cp -r public .next/standalone/public
echo "Standalone ready."
