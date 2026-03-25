#!/bin/bash
set -uo pipefail

mkdir -p /logs/verifier

TASK_ROOT="${TASK_ROOT:-/root}"
export TASK_ROOT

cd /tests

set +e
pytest -q /tests/test_outputs.py
status=$?
set -e

if [ "$status" -eq 0 ]; then
  printf '1\n' > /logs/verifier/reward.txt
else
  printf '0\n' > /logs/verifier/reward.txt
fi

exit "$status"
