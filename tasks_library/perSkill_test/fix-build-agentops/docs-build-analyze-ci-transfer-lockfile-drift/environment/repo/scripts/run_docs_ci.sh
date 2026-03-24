#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
DOCS_DIR="$ROOT_DIR/docs"

cd "$DOCS_DIR"
npm ci --ignore-scripts
npm run build

test -f "$DOCS_DIR/dist/index.html"
