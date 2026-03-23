#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

cd /root
suricata -V > /logs/verifier/suricata_version.txt 2>&1 || true

if python3 /tests/test_outputs.py; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

cp /root/local.rules /logs/verifier/local.rules 2>/dev/null || true
cp /root/suricata.yaml /logs/verifier/suricata.yaml 2>/dev/null || true

exit 0
