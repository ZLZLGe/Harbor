#!/bin/bash

mkdir -p /logs/verifier

PROJECT_ROOT="${TASK_PROJECT_ROOT:-/workspace/dispatch-board}"
export TASK_PROJECT_ROOT="$PROJECT_ROOT"

set +e
python -m pytest -q /tests/test_outputs.py
STATUS=$?
set -e

if [ "$STATUS" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

if [ -f "$PROJECT_ROOT/notes/async_contract_report.md" ]; then
  cp "$PROJECT_ROOT/notes/async_contract_report.md" /logs/verifier/async_contract_report.md
fi

exit "$STATUS"
