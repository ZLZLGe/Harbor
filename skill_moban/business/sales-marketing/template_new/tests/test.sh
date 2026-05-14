#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VERIFIER_LOG_ROOT="${VERIFIER_LOG_ROOT:-/logs/verifier}"
PYTHON_BIN="$(command -v python3 || command -v python)"
mkdir -p "$VERIFIER_LOG_ROOT"

if "$PYTHON_BIN" -m pytest -q "$SCRIPT_DIR/test_outputs.py" "$SCRIPT_DIR/test_guardrails.py" -rA \
  2>&1 | tee "$VERIFIER_LOG_ROOT/test-stdout.txt"; then
  printf '1.0\n' > "$VERIFIER_LOG_ROOT/reward.txt"
else
  printf '0.0\n' > "$VERIFIER_LOG_ROOT/reward.txt"
  exit 1
fi
