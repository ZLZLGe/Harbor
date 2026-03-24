#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p /logs/verifier

TEST_FILE="$SCRIPT_DIR/test_outputs.py"

if [ -f /root/build_merge_candidates.py ]; then
    cd /root
    python3 /root/build_merge_candidates.py
fi

if pytest "$TEST_FILE" \
    --ctrf=/logs/verifier/ctrf.json \
    -v 2>&1; then
    exit_code=0
else
    exit_code=$?
fi

if [ "$exit_code" -eq 0 ]; then
    echo "1" > /logs/verifier/reward.txt
else
    echo "0" > /logs/verifier/reward.txt
fi

cp /root/*.py /logs/verifier/ 2>/dev/null || true
cp /root/*.csv /logs/verifier/ 2>/dev/null || true
cp /root/*.json /logs/verifier/ 2>/dev/null || true

exit "$exit_code"
