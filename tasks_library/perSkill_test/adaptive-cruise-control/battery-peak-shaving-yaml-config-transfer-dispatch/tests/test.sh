#!/bin/bash

set -euo pipefail

pip3 install --break-system-packages \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5 \
    pandas==2.2.2 \
    pyyaml==6.0.1

TASK_ROOT="${TASK_ROOT:-/root}"
export TASK_ROOT

cd "$TASK_ROOT"
if [ -f "$TASK_ROOT/battery_peak_shaving.py" ]; then
    python3 "$TASK_ROOT/battery_peak_shaving.py"
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

pytest "$SCRIPT_DIR/test_outputs.py" \
    --ctrf=/logs/verifier/ctrf.json \
    -v 2>&1 || exit_code=$?

: "${exit_code:=0}"

if [ $exit_code -eq 0 ]; then
    echo "1" > /logs/verifier/reward.txt
else
    echo "0" > /logs/verifier/reward.txt
fi

cp "$TASK_ROOT"/*.py /logs/verifier/ 2>/dev/null || true
cp "$TASK_ROOT"/*.yaml /logs/verifier/ 2>/dev/null || true
cp "$TASK_ROOT"/*.csv /logs/verifier/ 2>/dev/null || true
cp "$TASK_ROOT"/*.md /logs/verifier/ 2>/dev/null || true

exit 0
