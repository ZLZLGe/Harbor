#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

if python3 /tests/test_outputs.py; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

cp -f /root/transfer2_sampler_manifest.csv /logs/verifier/transfer2_sampler_manifest.csv 2>/dev/null || true
cp -f /root/transfer2_sampler_reel.mp4 /logs/verifier/transfer2_sampler_reel.mp4 2>/dev/null || true
cp -rf /root/transfer2_clips /logs/verifier/transfer2_clips 2>/dev/null || true

exit 0
