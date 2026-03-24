#!/bin/bash
set -euo pipefail

ROOT="${TASK_ROOT:-/root}"
TEST_FILE="$(cd "$(dirname "$0")" && pwd)/test_outputs.py"

pip3 install --break-system-packages \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5 \
    pandas==2.2.2 \
    pyyaml==6.0.1 \
    numpy==1.26.4

if [ ! -f "$ROOT/tank_level_response.csv" ] && [ -f "$ROOT/simulate_tank.py" ] && [ -f "$ROOT/tank_tuning.yaml" ]; then
    python3 "$ROOT/simulate_tank.py"
fi

pytest "$TEST_FILE" \
    --ctrf=/logs/verifier/ctrf.json \
    -v

status=$?
if [ $status -eq 0 ]; then
    echo "1" > /logs/verifier/reward.txt
else
    echo "0" > /logs/verifier/reward.txt
fi

exit $status
