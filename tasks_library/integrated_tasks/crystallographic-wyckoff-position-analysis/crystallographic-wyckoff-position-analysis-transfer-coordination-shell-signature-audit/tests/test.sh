#!/bin/bash
set -euo pipefail

echo "=========================================="
echo "Agent's coordination_shell_signature.py:"
echo "=========================================="
cat /root/workspace/coordination_shell_signature.py

echo ""
echo "=========================================="
echo "Running coordination-shell tests..."
echo "=========================================="

python3 /tests/test_outputs.py

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
    echo "Writing default score: 0.0"
    echo "=========================================="
    mkdir -p /logs/verifier
    echo "0.0" > /logs/verifier/reward.txt
fi
