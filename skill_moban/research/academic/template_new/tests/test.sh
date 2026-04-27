#!/usr/bin/env bash
set -euo pipefail

mkdir -p /logs/verifier

if python -m pytest /tests/test_outputs.py -q --tb=short > /logs/verifier/pytest-output.txt 2>&1; then
  echo 1 > /logs/verifier/reward.txt
  cat /logs/verifier/pytest-output.txt
else
  echo 0 > /logs/verifier/reward.txt
  cat /logs/verifier/pytest-output.txt
  exit 1
fi
