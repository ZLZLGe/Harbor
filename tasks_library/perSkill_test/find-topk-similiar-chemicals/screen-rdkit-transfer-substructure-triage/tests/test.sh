#!/bin/bash

echo "=========================================="
echo "Installing dependencies..."
echo "=========================================="

pip3 install --break-system-packages pytest==8.3.4 pytest-json-report==1.5.0 --quiet 2>/dev/null || true

echo ""
echo "=========================================="
echo "Agent's substructure_triage.py:"
echo "=========================================="
cat /root/workspace/substructure_triage.py 2>/dev/null || echo "ERROR: substructure_triage.py not found"

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
    echo "WARNING: No reward.txt generated (test crashed or failed)"
    echo "Writing default score: 0.0"
    echo "=========================================="
    echo "0.0" > /logs/verifier/reward.txt
fi

exit 0
