#!/bin/bash
set -euo pipefail

APP_DIR="${APP_DIR:-/app}"
TEST_LOG="/logs/verifier/test.log"
REWARD_FILE="/logs/verifier/reward.txt"

mkdir -p /logs/verifier

set +e
python /tests/test_outputs.py >"${TEST_LOG}" 2>&1
test_status=$?
set -e

if [ "${test_status}" -eq 0 ]; then
  echo "1.0" > "${REWARD_FILE}"
else
  echo "0.0" > "${REWARD_FILE}"
fi

if [ -f "${APP_DIR}/build_boundary_report.json" ]; then
  cp "${APP_DIR}/build_boundary_report.json" /logs/verifier/build_boundary_report.json
fi

exit "${test_status}"
