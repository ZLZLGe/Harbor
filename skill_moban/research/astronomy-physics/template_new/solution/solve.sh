#!/usr/bin/env bash
set -euo pipefail

cp /solution/fixed/build_followup_packet.py /root/environment/pipeline/build_followup_packet.py
cp /solution/fixed/build_followup_packet.py /root/workspace/build_followup_packet.py
chmod +x /root/environment/pipeline/build_followup_packet.py /root/workspace/build_followup_packet.py

python /root/environment/pipeline/build_followup_packet.py \
  --data /root/environment/data \
  --output /root/answer
