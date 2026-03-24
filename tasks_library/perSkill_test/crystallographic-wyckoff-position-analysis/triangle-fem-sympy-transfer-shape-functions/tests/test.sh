#!/bin/bash

echo "=========================================="
echo "Agent's triangle_shape_functions.py:"
echo "=========================================="
cat /root/workspace/triangle_shape_functions.py

echo ""
echo "=========================================="
echo "Running tests..."
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

exit 0
