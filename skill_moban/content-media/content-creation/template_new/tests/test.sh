#!/bin/bash
set -uo pipefail

VERIFIER_LOG_ROOT="${VERIFIER_LOG_ROOT:-/logs/verifier}"
mkdir -p "$VERIFIER_LOG_ROOT"

cd /app

if python3 -m pytest --ctrf "$VERIFIER_LOG_ROOT/ctrf.json" /tests/test_outputs.py /tests/test_guardrails.py -rA -v "$@" \
  | tee "$VERIFIER_LOG_ROOT/pytest-output.txt"; then
  printf '1.0\n' > "$VERIFIER_LOG_ROOT/reward.txt"
else
  printf '0.0\n' > "$VERIFIER_LOG_ROOT/reward.txt"
fi

cp /app/output/core_angle.md "$VERIFIER_LOG_ROOT/" 2>/dev/null || true
cp /app/output/x_thread.md "$VERIFIER_LOG_ROOT/" 2>/dev/null || true
cp /app/output/linkedin_post.md "$VERIFIER_LOG_ROOT/" 2>/dev/null || true
cp /app/output/newsletter.md "$VERIFIER_LOG_ROOT/" 2>/dev/null || true
cp /app/output/short_video_script.md "$VERIFIER_LOG_ROOT/" 2>/dev/null || true
cp /app/output/manifest.json "$VERIFIER_LOG_ROOT/" 2>/dev/null || true

exit 0
