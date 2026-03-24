#!/bin/bash

echo "=========================================="
echo "Agent's analog_ranking.py:"
echo "=========================================="
cat /root/workspace/analog_ranking.py 2>/dev/null || echo "ERROR: analog_ranking.py not found"

echo ""
echo "=========================================="
echo "Running tests..."
echo "=========================================="

mkdir -p /logs/verifier

set +e
python3 /tests/test_outputs.py
TEST_EXIT_CODE=$?
set -e

if [ -f "/logs/verifier/reward.txt" ]; then
    echo ""
    echo "=========================================="
    echo "Test completed. Score:"
    cat /logs/verifier/reward.txt
    echo "=========================================="
else
    echo ""
    echo "=========================================="
    echo "WARNING: No reward.txt generated"
    echo "=========================================="
    echo "0.0" > /logs/verifier/reward.txt
fi

exit 0
