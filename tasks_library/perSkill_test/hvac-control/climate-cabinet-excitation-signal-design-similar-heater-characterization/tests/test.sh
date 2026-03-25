#!/bin/bash
set -u

mkdir -p /logs/verifier

cd /root || exit 1
pytest /tests/test_outputs.py -q
test_exit_code=$?

if [ "$test_exit_code" -eq 0 ]; then
  echo "1" > /logs/verifier/reward.txt
else
  echo "0" > /logs/verifier/reward.txt
fi

cp /root/chamber_characterization.json /logs/verifier/ 2>/dev/null || true

exit 0
