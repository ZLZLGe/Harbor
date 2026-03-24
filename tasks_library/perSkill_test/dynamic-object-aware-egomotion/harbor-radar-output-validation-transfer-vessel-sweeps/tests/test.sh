#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

set +e
python3 -m pytest /tests/test_outputs.py -rA -v
test_status=$?
set -e

if [ "${test_status}" -eq 0 ]; then
  printf '1.0\n' > /logs/verifier/reward.txt
else
  printf '0.0\n' > /logs/verifier/reward.txt
fi

cp /root/pred_harbor_tracks.json /logs/verifier/pred_harbor_tracks.json 2>/dev/null || true
cp /root/pred_harbor_echo_masks.npz /logs/verifier/pred_harbor_echo_masks.npz 2>/dev/null || true

exit "${test_status}"
