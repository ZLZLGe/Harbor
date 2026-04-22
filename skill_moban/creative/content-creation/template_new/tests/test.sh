#!/bin/bash
set -euo pipefail

TESTS_ROOT="${TESTS_ROOT:-/tests}"
VERIFIER_LOG_ROOT="${VERIFIER_LOG_ROOT:-/logs/verifier}"

mkdir -p "$VERIFIER_LOG_ROOT"

set +e
set -o pipefail
python -m pytest -q "$TESTS_ROOT/test_outputs.py" "$TESTS_ROOT/test_guardrails.py" 2>&1 | tee "$VERIFIER_LOG_ROOT/pytest-output.txt"
PYTEST_EXIT=${PIPESTATUS[0]}
set +o pipefail
set -e

if [ "$PYTEST_EXIT" -eq 0 ]; then
  echo 1 > "$VERIFIER_LOG_ROOT/reward.txt"
else
  echo 0 > "$VERIFIER_LOG_ROOT/reward.txt"
fi

exit 0
