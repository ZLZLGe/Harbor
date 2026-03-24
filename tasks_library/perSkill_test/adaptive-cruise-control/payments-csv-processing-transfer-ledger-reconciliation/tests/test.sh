#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p /logs/verifier

TEST_FILE="$SCRIPT_DIR/test_outputs.py"

if [ -f /root/reconcile_ledgers.py ]; then
    python3 /root/reconcile_ledgers.py
fi

if pytest "$TEST_FILE" \
    --ctrf=/logs/verifier/ctrf.json \
    -v 2>&1; then
    exit_code=0
else
    exit_code=$?
fi

if [ $exit_code -eq 0 ]; then
    echo "1" > /logs/verifier/reward.txt
else
    echo "0" > /logs/verifier/reward.txt
fi

cp /root/reconcile_ledgers.py /logs/verifier/ 2>/dev/null || true
cp /root/reconciliation_exceptions.csv /logs/verifier/ 2>/dev/null || true
cp /root/reconciliation_summary.json /logs/verifier/ 2>/dev/null || true

exit "$exit_code"
