#!/bin/bash
set -euo pipefail

TESTS_ROOT="${TESTS_ROOT:-/tests}"
VERIFIER_LOG_ROOT="${VERIFIER_LOG_ROOT:-/logs/verifier}"

mkdir -p "$VERIFIER_LOG_ROOT"

if ! curl -fsS http://127.0.0.1:8331/health >/dev/null 2>&1; then
  nohup python3 /services/audit-service/server.pyc >/tmp/marketplace-audit.log 2>&1 &
  API_PID=$!
  trap 'kill $API_PID 2>/dev/null || true' EXIT
  for i in {1..30}; do
    if curl -fsS http://127.0.0.1:8331/health >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
fi

set +e
set -o pipefail
pytest -q "$TESTS_ROOT/test_outputs.py" "$TESTS_ROOT/test_guardrails.py" 2>&1 | tee "$VERIFIER_LOG_ROOT/pytest-output.txt"
PYTEST_EXIT=${PIPESTATUS[0]}
set +o pipefail
set -e

if [ "$PYTEST_EXIT" -eq 0 ]; then
  echo 1 > "$VERIFIER_LOG_ROOT/reward.txt"
else
  echo 0 > "$VERIFIER_LOG_ROOT/reward.txt"
fi

exit 0
