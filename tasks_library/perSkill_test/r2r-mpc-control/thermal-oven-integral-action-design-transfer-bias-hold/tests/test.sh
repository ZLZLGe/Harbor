#!/bin/bash

mkdir -p /logs/verifier

TASK_ROOT="${TASK_ROOT:-/root}"
cd "$TASK_ROOT"
export PYTHONPATH="$TASK_ROOT:$TASK_ROOT/environment:${PYTHONPATH:-}"

set +e
pytest /tests/test_outputs.py -q
TEST_EXIT_CODE=$?
set -e

if [ "$TEST_EXIT_CODE" -eq 0 ]; then
    echo "1" > /logs/verifier/reward.txt
else
    echo "0" > /logs/verifier/reward.txt
fi

cp /root/heater_integrator_config.json /logs/verifier/ 2>/dev/null || true

exit 0
