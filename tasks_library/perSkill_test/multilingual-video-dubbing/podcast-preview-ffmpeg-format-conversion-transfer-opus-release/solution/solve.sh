#!/bin/bash
set -euo pipefail

mkdir -p /outputs

ffmpeg -y \
  -i /root/podcast_preview_master.wav \
  -c:a libopus \
  -application audio \
  -b:a 64k \
  -vbr constrained \
  -ar 48000 \
  -ac 2 \
  /outputs/podcast_preview.opus
