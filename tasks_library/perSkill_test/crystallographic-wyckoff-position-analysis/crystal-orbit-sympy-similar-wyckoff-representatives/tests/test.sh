#!/bin/bash
set -e

pip3 install --break-system-packages pytest==8.3.4 pytest-json-report==1.5.0 --quiet || true

echo "=========================================="
echo "Agent's wyckoff_orbit_solver.py:"
echo "=========================================="
cat /root/workspace/wyckoff_orbit_solver.py

echo ""
echo "=========================================="
echo "Running tests..."
echo "=========================================="

python3 /tests/test_outputs.py
