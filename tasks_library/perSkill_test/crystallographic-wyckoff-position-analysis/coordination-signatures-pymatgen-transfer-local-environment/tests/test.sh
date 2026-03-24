#!/bin/bash
set -euo pipefail

echo "=========================================="
echo "Installing verifier dependencies..."
echo "=========================================="
pip3 install --break-system-packages pytest==8.3.4 pytest-json-report==1.5.0 --quiet || true

echo ""
echo "=========================================="
echo "Agent's solution.py:"
echo "=========================================="
cat /root/workspace/solution.py

echo ""
echo "=========================================="
echo "Running verification..."
echo "=========================================="
python3 /tests/test_outputs.py

if [ -f "/logs/verifier/reward.txt" ]; then
    echo ""
    echo "=========================================="
    echo "Score:"
    cat /logs/verifier/reward.txt
    echo "=========================================="
else
    echo ""
    echo "=========================================="
    echo "WARNING: reward.txt missing; writing 0.0"
    echo "=========================================="
    mkdir -p /logs/verifier
    echo "0.0" > /logs/verifier/reward.txt
fi
