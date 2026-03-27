#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

if python3 -m pytest /tests/test_outputs.py -q; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

for f in /root/*.docx; do
  [ -f "$f" ] && cp -f "$f" /logs/verifier/ || true
done

exit 0
