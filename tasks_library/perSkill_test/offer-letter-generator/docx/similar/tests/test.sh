#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

if python3 -m pytest /tests/test_outputs.py -q; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

cp -f /root/similar_offer_letter_filled.docx /logs/verifier/ 2>/dev/null || true

exit 0
