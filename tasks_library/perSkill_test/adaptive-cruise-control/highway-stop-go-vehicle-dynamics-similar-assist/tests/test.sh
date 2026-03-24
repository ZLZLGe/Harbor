#!/bin/bash
set -euo pipefail

ROOT_DIR="${TASK_ROOT:-/root}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="/logs/verifier"
REWARD_FILE="${LOG_DIR}/reward.txt"
LOG_FILE="${LOG_DIR}/test.log"

mkdir -p "${LOG_DIR}"

test_status=0

set +e
if [ -f "${ROOT_DIR}/stop_go_simulation.py" ]; then
    python3 "${ROOT_DIR}/stop_go_simulation.py" >"${LOG_FILE}" 2>&1
    test_status=$?
else
    : >"${LOG_FILE}"
fi

if [ "${test_status}" -eq 0 ]; then
    python3 "${SCRIPT_DIR}/test_outputs.py" >>"${LOG_FILE}" 2>&1
    test_status=$?
fi
set -e

if [ "${test_status}" -eq 0 ]; then
    printf '1.0\n' >"${REWARD_FILE}"
else
    printf '0.0\n' >"${REWARD_FILE}"
fi

exit "${test_status}"
