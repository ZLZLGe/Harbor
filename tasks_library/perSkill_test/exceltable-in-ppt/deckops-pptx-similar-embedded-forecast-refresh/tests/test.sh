#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

set +e
python3 /tests/test_outputs.py
test_status=$?
set -e

if [ "$test_status" -eq 0 ]; then
    printf "1.0\n" > /logs/verifier/reward.txt
else
    printf "0.0\n" > /logs/verifier/reward.txt
fi

if [ -f "/root/revenue-forecast-refresh.pptx" ]; then
    cp /root/revenue-forecast-refresh.pptx /logs/verifier/revenue-forecast-refresh.pptx 2>/dev/null || true
fi

exit "$test_status"
