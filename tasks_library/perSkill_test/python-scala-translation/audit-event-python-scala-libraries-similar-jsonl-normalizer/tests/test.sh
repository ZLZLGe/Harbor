#!/bin/bash
set -e

mkdir -p /logs/verifier

if python3 /tests/test_outputs.py /root/EventNormalizer.scala /root/localtest > /logs/verifier/output.log 2>&1; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit 0
