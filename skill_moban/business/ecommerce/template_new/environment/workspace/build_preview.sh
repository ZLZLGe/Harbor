#!/bin/bash
set -euo pipefail

ROOT="${WORKSPACE_ROOT:-/app/workspace}"

cd "$ROOT"
mkdir -p "$ROOT/out"
rm -f "$ROOT/out/collection.html" "$ROOT/out/predictive-search.html" "$ROOT/out/theme_preview_report.json"

npm run build-preview
npm run export-report
