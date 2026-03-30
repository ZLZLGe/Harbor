#!/bin/bash

set -uo pipefail

mkdir -p /logs/verifier

export PGHOST=/tmp/support-dashboard-pg
export PGPORT=55432
export PGUSER=postgres
export PYTHONUNBUFFERED=1

START_LOG=/logs/verifier/postgres_start.log
TEST_LOG=/logs/verifier/test_output.log
EXIT_CODE=0

if ! /workspace/environment/bin/start-postgres.sh >"$START_LOG" 2>&1; then
  cat "$START_LOG" >"$TEST_LOG"
  EXIT_CODE=1
else
  set +e
  python3 -m pytest -rA -v /tests/test_outputs.py 2>&1 | tee "$TEST_LOG"
  EXIT_CODE=${PIPESTATUS[0]}
  set -e
fi

if [ "$EXIT_CODE" -eq 0 ]; then
  echo 1 >/logs/verifier/reward.txt
else
  echo 0 >/logs/verifier/reward.txt
fi

/workspace/environment/bin/stop-postgres.sh >/dev/null 2>&1 || true
exit 0
