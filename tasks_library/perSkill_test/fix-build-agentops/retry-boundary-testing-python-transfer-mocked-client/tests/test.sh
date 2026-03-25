#!/usr/bin/env bash
set -u

mkdir -p /logs/verifier

PROJECT_ROOT="${TASK_PROJECT_ROOT:-/workspace/billing-relay}"
export TASK_PROJECT_ROOT="$PROJECT_ROOT"

TEST_EXIT_CODE=0
python -m pytest -q /tests/test_outputs.py -rA
TEST_EXIT_CODE=$?

if [ "$TEST_EXIT_CODE" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

if [ -f "$PROJECT_ROOT/reports/mock_retry_audit.txt" ]; then
  cp "$PROJECT_ROOT/reports/mock_retry_audit.txt" /logs/verifier/mock_retry_audit.txt
fi

exit "$TEST_EXIT_CODE"
