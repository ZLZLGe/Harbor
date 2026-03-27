#!/bin/bash
set -euo pipefail
mkdir -p /logs/verifier

if python -m pytest /tests/test_outputs.py -rA -v; then
    printf "1.0\n" > /logs/verifier/reward.txt
else
    status=$?
    printf "0.0\n" > /logs/verifier/reward.txt
    exit "$status"
fi
