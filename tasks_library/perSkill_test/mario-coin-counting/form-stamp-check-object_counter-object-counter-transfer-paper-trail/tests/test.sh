#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

python3 -m pip install --break-system-packages pytest==8.4.1

if python3 -m pytest /tests/test_outputs.py -rA -v; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi
