#!/bin/bash

mkdir -p /logs/verifier

set +e
pytest -q /tests/test_outputs.py
status=$?
set -e

if [ "$status" -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi

if [ -f /root/makeup_gradebook.xlsx ]; then
    cp /root/makeup_gradebook.xlsx /logs/verifier/makeup_gradebook.xlsx 2>/dev/null || true
fi

exit "$status"
