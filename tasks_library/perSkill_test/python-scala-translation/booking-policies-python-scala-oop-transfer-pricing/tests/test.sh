#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

if python3 /tests/test_outputs.py /root/BookingPolicies.scala /root/BookingPolicies.py /root/pricing_scenarios.json > /logs/verifier/output.log 2>&1; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit 0
