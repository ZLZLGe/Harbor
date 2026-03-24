#!/bin/bash
set -euo pipefail

ROOT_DIR="${TASK_ROOT:-/root}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEST_LOG="/logs/verifier/test.log"

mkdir -p /logs/verifier

test_status=0

set +e
if [ -f "${ROOT_DIR}/tram_platform_sim.py" ]; then
    python3 "${ROOT_DIR}/tram_platform_sim.py" >"${TEST_LOG}" 2>&1
    test_status=$?
else
    printf 'missing /root/tram_platform_sim.py\n' >"${TEST_LOG}"
    test_status=1
fi

if [ "${test_status}" -eq 0 ]; then
    python3 "${SCRIPT_DIR}/test_outputs.py" >>"${TEST_LOG}" 2>&1
    test_status=$?
fi

set -e

if [ "${test_status}" -eq 0 ]; then
    printf '1.0\n' >/logs/verifier/reward.txt
else
    printf '0.0\n' >/logs/verifier/reward.txt
fi

exit "${test_status}"
