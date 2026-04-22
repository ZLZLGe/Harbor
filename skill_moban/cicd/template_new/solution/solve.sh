#!/bin/bash
set -euo pipefail

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/app/workspace}"
SOLUTION_ROOT="${SOLUTION_ROOT:-/solution}"

cp "$SOLUTION_ROOT/fixed/release-dry-run.yml" \
  "$WORKSPACE_ROOT/.github/workflows/release-dry-run.yml"
cp "$SOLUTION_ROOT/fixed/build_bundle.py" \
  "$WORKSPACE_ROOT/scripts/build_bundle.py"
cp "$SOLUTION_ROOT/fixed/collect_provenance.py" \
  "$WORKSPACE_ROOT/scripts/collect_provenance.py"
