#!/bin/bash

set -u -o pipefail

mkdir -p /logs/verifier

rc=0
python3 -m pytest -q /tests/test_outputs.py || rc=$?

if [ "$rc" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit "$rc"
