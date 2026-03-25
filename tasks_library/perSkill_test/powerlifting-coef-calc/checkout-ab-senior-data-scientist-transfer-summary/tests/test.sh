#!/bin/bash
set -u

mkdir -p /logs/verifier

set +e
pytest /tests/test_outputs.py -q
status=$?
set -e

if [ "$status" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

if [ -f "/root/results/checkout_experiment_summary.json" ]; then
  cp /root/results/checkout_experiment_summary.json /logs/verifier/checkout_experiment_summary.json
fi

exit "$status"
