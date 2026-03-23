#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier
if python3 /tests/test_outputs.py; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

if [ -f /root/transfer3_energy_delta.json ]; then
  cp /root/transfer3_energy_delta.json /logs/verifier/
fi

exit 0
