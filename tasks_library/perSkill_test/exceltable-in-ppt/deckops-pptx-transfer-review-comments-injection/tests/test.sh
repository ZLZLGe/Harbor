#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

test_status=0
set +e
python3 /tests/test_outputs.py
test_status=$?
set -e

if [ "$test_status" -eq 0 ]; then
    echo "1.0" > /logs/verifier/reward.txt
else
    echo "0.0" > /logs/verifier/reward.txt
fi

if [ -f "/root/review-comments-injected.pptx" ]; then
    cp /root/review-comments-injected.pptx /logs/verifier/review-comments-injected.pptx 2>/dev/null || true
fi

exit "$test_status"
