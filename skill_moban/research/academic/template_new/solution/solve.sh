#!/bin/bash
set -euo pipefail

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/app/workspace}"
SOLUTION_ROOT="${SOLUTION_ROOT:-/solution}"

cp "$SOLUTION_ROOT/fixed_included_studies.csv" "$WORKSPACE_ROOT/included_studies.csv"
cp "$SOLUTION_ROOT/fixed_references.bib" "$WORKSPACE_ROOT/references.bib"
cp "$SOLUTION_ROOT/fixed_summary.md" "$WORKSPACE_ROOT/summary.md"

python3 "$WORKSPACE_ROOT/build_submission.py"
