#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p /logs/verifier

cd /root
if [ -f /root/analyze_excursions.py ]; then
    python3 /root/analyze_excursions.py
fi

if pytest "$SCRIPT_DIR/test_outputs.py" -v; then
    echo "1" > /logs/verifier/reward.txt
else
    echo "0" > /logs/verifier/reward.txt
    exit 1
fi
