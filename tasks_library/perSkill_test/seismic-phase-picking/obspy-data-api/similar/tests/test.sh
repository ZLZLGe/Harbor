#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

if python3 /tests/test_outputs.py; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

for pattern in /root/*.csv /root/*.json; do
  if [ -e "$pattern" ]; then
    cp -f "$pattern" /logs/verifier/
  fi
done

exit 0
