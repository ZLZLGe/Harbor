#!/bin/bash

set -u

export TASK_OUTPUT_FILE="${TASK_OUTPUT_FILE:-/root/data/readmission_risk_dashboard.xlsx}"

if python3 /tests/test_outputs.py; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
  exit 1
fi

if [ -f "$TASK_OUTPUT_FILE" ]; then
  cp "$TASK_OUTPUT_FILE" /logs/verifier/readmission_risk_dashboard.xlsx
fi
