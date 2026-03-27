#!/bin/bash
set -euo pipefail

mkdir -p /outputs

ffmpeg -y -loglevel error \
  -i /root/input.mp4 \
  -vf "scale=640:360:flags=lanczos,eq=brightness=0.04:contrast=1.08,boxblur=1:1" \
  -c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p \
  -c:a aac -b:a 128k -ar 48000 -ac 1 \
  /outputs/similar_preview.mp4
