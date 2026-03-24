#!/bin/bash

set -uo pipefail

python3 -m pip install --break-system-packages \
  pytest==8.4.1 \
  pytest-json-ctrf==0.3.5

mkdir -p /logs/verifier

status=0

python3 -m pytest \
  --ctrf /logs/verifier/ctrf.json \
  /tests/test_outputs.py \
  -rA || status=$?

if [ $status -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit $status
