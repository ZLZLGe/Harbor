#!/bin/bash
set -euo pipefail

SOLUTION_ROOT="${SOLUTION_ROOT:-/solution}"
OUTPUT_ROOT="${OUTPUT_ROOT:-/app/output}"

mkdir -p "$OUTPUT_ROOT/deck"

cp "$SOLUTION_ROOT/fixed/index.html" \
  "$OUTPUT_ROOT/deck/index.html"
python3 "$SOLUTION_ROOT/build_fixed_submission.py"
