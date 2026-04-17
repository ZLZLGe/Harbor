#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

cd /root
pytest /tests/test_outputs.py -v -rA
status=$?

if [ "$status" -eq 0 ]; then
  echo "1" > /logs/verifier/reward.txt
else
  echo "0" > /logs/verifier/reward.txt
fi

cp /root/*.json /logs/verifier/ 2>/dev/null || true

exit 0
