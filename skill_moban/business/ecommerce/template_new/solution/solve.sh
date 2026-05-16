#!/bin/bash
set -euo pipefail

ROOT="${WORKSPACE_ROOT:-/app/workspace}"
SOLUTION_ROOT="$(cd "$(dirname "$0")" && pwd)/fixed"

cp "$SOLUTION_ROOT/theme/sections/main-collection.liquid" "$ROOT/theme/sections/main-collection.liquid"
cp "$SOLUTION_ROOT/theme/sections/predictive-search.liquid" "$ROOT/theme/sections/predictive-search.liquid"
cp "$SOLUTION_ROOT/theme/snippets/product-card.liquid" "$ROOT/theme/snippets/product-card.liquid"
cp "$SOLUTION_ROOT/scripts/build-preview.mjs" "$ROOT/scripts/build-preview.mjs"
cp "$SOLUTION_ROOT/scripts/export-report.mjs" "$ROOT/scripts/export-report.mjs"
mkdir -p "$ROOT/scripts/lib"
cp "$SOLUTION_ROOT/scripts/lib/catalog.mjs" "$ROOT/scripts/lib/catalog.mjs"

bash "$ROOT/build_preview.sh"
