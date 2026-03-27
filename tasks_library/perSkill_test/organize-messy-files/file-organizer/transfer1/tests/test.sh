#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

if python3 -m pytest -q /tests/test_outputs.py; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

for f in /root/transfer1_keep_decisions.csv; do
  if [ -f "$f" ]; then
    cp "$f" /logs/verifier/
  fi
done

exit 0
