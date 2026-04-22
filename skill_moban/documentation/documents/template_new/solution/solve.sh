#!/bin/bash
set -euo pipefail

mkdir -p /app/output

python3 /app/.codex/skills/word-redline-workflows/scripts/apply_redline_decisions.py \
  --input /app/vendor_addendum_redline.docx \
  --decisions /app/review_decisions.json \
  --output /app/output/vendor_addendum_final.docx
