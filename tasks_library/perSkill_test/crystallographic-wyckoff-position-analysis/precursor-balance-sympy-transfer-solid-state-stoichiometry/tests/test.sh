#!/bin/bash

pip3 install --break-system-packages pytest==8.3.4 pytest-json-report==1.5.0 --quiet || true

echo "=========================================="
echo "Agent's solid_state_stoichiometry.py:"
echo "=========================================="
cat /root/workspace/solid_state_stoichiometry.py

echo ""
echo "=========================================="
echo "Running tests..."
echo "=========================================="

python3 /tests/test_outputs.py
