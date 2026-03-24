#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p /logs/verifier

cd /root

if [ -f /root/build_mode_audit.py ]; then
    python3 /root/build_mode_audit.py
fi

TEST_FILE="$SCRIPT_DIR/test_outputs.py"

set +e
pytest "$TEST_FILE" \
    --ctrf=/logs/verifier/ctrf.json \
    -v
exit_code=$?
set -e

if [ $exit_code -eq 0 ]; then
    echo "1" > /logs/verifier/reward.txt
else
    echo "0" > /logs/verifier/reward.txt
fi

exit $exit_code
