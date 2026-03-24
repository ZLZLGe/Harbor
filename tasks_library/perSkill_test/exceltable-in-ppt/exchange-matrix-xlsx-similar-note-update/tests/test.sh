#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

if [ -f "/root/results_exchange_matrix.xlsx" ]; then
    cp /root/results_exchange_matrix.xlsx /logs/verifier/results_exchange_matrix.xlsx 2>/dev/null || true
fi

status=0
python3 -m pytest \
    --ctrf /logs/verifier/ctrf.json \
    /tests/test_outputs.py \
    -rA || status=$?

if [ $status -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi

exit $status
