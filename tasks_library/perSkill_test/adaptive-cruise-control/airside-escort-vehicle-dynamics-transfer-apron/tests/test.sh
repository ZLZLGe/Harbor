#!/bin/bash
set -euo pipefail

pip3 install --break-system-packages \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5 \
    pandas==2.2.2 \
    pyyaml==6.0.1

ROOT_DIR="${TASK_ROOT:-/root}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEST_FILE="${SCRIPT_DIR}/test_outputs.py"

if [ -f "${ROOT_DIR}/escort_simulation.py" ]; then
    python3 "${ROOT_DIR}/escort_simulation.py"
fi

set +e
pytest "${TEST_FILE}" \
    --ctrf=/logs/verifier/ctrf.json \
    -v 2>&1

exit_code=$?
set -e

if [ "${exit_code}" -eq 0 ]; then
    echo "1" > /logs/verifier/reward.txt
else
    echo "0" > /logs/verifier/reward.txt
fi

cp "${ROOT_DIR}"/*.py /logs/verifier/ 2>/dev/null || true
cp "${ROOT_DIR}"/*.yaml /logs/verifier/ 2>/dev/null || true
cp "${ROOT_DIR}"/*.csv /logs/verifier/ 2>/dev/null || true

exit 0
