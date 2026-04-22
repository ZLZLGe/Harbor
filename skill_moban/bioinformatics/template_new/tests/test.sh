#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier
REWARD_FILE="/logs/verifier/reward.txt"
RESULT_FILE="/logs/verifier/result.json"

python /services/panel-annotation/server.py >/tmp/panel-annotation-test.log 2>&1 &
SERVICE_PID=$!
trap 'kill ${SERVICE_PID} >/dev/null 2>&1 || true' EXIT

if python -m pytest -q /tests/test_outputs.py; then
  printf '1.0\n' > "${REWARD_FILE}"
  printf '{"reward": 1.0}\n' > "${RESULT_FILE}"
else
  printf '0.0\n' > "${REWARD_FILE}"
  printf '{"reward": 0.0}\n' > "${RESULT_FILE}"
fi
