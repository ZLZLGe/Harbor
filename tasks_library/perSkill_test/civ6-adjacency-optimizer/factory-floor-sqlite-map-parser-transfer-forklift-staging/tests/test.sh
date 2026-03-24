#!/bin/bash
set -euo pipefail

TESTS_DIR="${TESTS_DIR:-/tests}"
OUTPUT_DIR="${OUTPUT_DIR:-/output}"
LOG_DIR="${LOG_DIR:-/logs/verifier}"

mkdir -p "${LOG_DIR}/scores" "${LOG_DIR}/solutions"
cp "${OUTPUT_DIR}/forklift_staging_plan.json" "${LOG_DIR}/solutions/" 2>/dev/null || true

set +e
python3 "${TESTS_DIR}/test_outputs.py" > "${LOG_DIR}/test_output.log" 2>&1
TEST_EXIT_CODE=$?
set -e

cat "${LOG_DIR}/test_output.log"

if [ "${TEST_EXIT_CODE}" -eq 0 ]; then
  SCORE="1.0"
else
  SCORE="0.0"
fi

printf '%s' "${SCORE}" > "${LOG_DIR}/scores/forklift_staging_plan.txt"
printf '%s' "${SCORE}" > "${LOG_DIR}/reward.txt"

exit 0
