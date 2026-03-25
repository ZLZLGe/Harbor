#!/bin/bash

set -u

mkdir -p /logs/verifier

python3 -m pytest /tests/test_outputs.py -rA
test_exit_code=$?

if [ "$test_exit_code" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

if [ -f "/root/data/commission_payout_audit.xlsx" ]; then
  cp /root/data/commission_payout_audit.xlsx /logs/verifier/commission_payout_audit.xlsx
fi

exit "$test_exit_code"
