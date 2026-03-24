#!/bin/bash
set -euo pipefail

ROOT_DIR="${TASK_ROOT:-/root}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="/logs/verifier"

mkdir -p "${LOG_DIR}"

set +e
if [ -f "${ROOT_DIR}/tugger_convoy_sim.py" ]; then
    python3 "${ROOT_DIR}/tugger_convoy_sim.py" >"${LOG_DIR}/test_output.txt" 2>&1
    status=$?
else
    : >"${LOG_DIR}/test_output.txt"
    status=0
fi

if [ "${status}" -eq 0 ]; then
    python3 "${SCRIPT_DIR}/test_outputs.py" >>"${LOG_DIR}/test_output.txt" 2>&1
    status=$?
else
    python3 "${SCRIPT_DIR}/test_outputs.py" >>"${LOG_DIR}/test_output.txt" 2>&1
    verifier_status=$?
    if [ "${verifier_status}" -eq 0 ]; then
        :
    fi
fi
set -e

if [ "${status}" -eq 0 ]; then
    printf '1.0\n' >"${LOG_DIR}/reward.txt"
else
    printf '0.0\n' >"${LOG_DIR}/reward.txt"
fi

exit "${status}"
