#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

if python3 -m pytest /tests/test_outputs.py -q; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

for path in /root/transfer2_call_batch.flac /root/transfer2_call_batch_report.json; do
  if [ -f "$path" ]; then
    cp "$path" /logs/verifier/
  fi
done

exit 0
