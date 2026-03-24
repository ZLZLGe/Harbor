#!/bin/bash
set -euo pipefail

VERIFIER_LOG_DIR="${VERIFIER_LOG_DIR:-/logs/verifier}"

mkdir -p "${VERIFIER_LOG_DIR}"

export TASK_ROOT="${TASK_ROOT:-/root}"
export TASK_TESTS_DIR="${TASK_TESTS_DIR:-/tests}"

python3 "${TASK_TESTS_DIR}/test_outputs.py"
TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "1" > "${VERIFIER_LOG_DIR}/reward.txt"
else
    echo "0" > "${VERIFIER_LOG_DIR}/reward.txt"
fi

cp "${TASK_ROOT}"/*.json "${VERIFIER_LOG_DIR}/" 2>/dev/null || true

exit 0
