#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

if pytest /tests/test_outputs.py -rA -v; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
  exit 1
fi
