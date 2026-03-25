#!/bin/bash
set -uo pipefail

mkdir -p /logs/verifier

pytest_exit=0
python3 -m pytest /tests/test_outputs.py -rA -v
pytest_exit=$?

cp /root/evidence_index.json /logs/verifier/evidence_index.json 2>/dev/null || true
cp -r /root/evidence_frames /logs/verifier/evidence_frames 2>/dev/null || true

if [ "$pytest_exit" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit "$pytest_exit"
