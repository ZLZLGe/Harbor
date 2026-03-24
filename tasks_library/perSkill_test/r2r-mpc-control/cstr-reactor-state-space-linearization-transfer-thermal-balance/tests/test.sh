#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

echo "=== Contents of /root ==="
ls -la /root/ 2>&1

cd /root
if [ -f /tests/test_outputs.py ]; then
  TEST_FILE="/tests/test_outputs.py"
else
  TEST_FILE="$(cd "$(dirname "$0")" && pwd)/test_outputs.py"
fi

python3 "$TEST_FILE" 2>&1 | tee /logs/verifier/test.log
TEST_EXIT_CODE=${PIPESTATUS[0]}

if [ "$TEST_EXIT_CODE" -eq 0 ]; then
  echo "1" > /logs/verifier/reward.txt
else
  echo "0" > /logs/verifier/reward.txt
fi

cp -r /root/artifacts /logs/verifier/ 2>/dev/null || true

exit 0
