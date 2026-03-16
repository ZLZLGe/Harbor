#!/bin/bash
set -euo pipefail

pip3 install --break-system-packages pytest pytest-json-ctrf

mkdir -p /logs/verifier

set +e
pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA -v
status=$?
set -e

if [ $status -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit $status
