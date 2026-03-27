#!/bin/bash
set -euo pipefail

mkdir -p /outputs

ffmpeg -y -loglevel error \
  -i /root/input.mp4 \
  -vf "scale=854:480:flags=lanczos,unsharp=5:5:0.6:3:3:0.0,setpts=0.8*PTS" \
  -af "atempo=1.25" \
  -c:v libx264 -preset veryfast -crf 22 -pix_fmt yuv420p \
  -c:a aac -b:a 128k -ar 48000 -ac 1 \
  /outputs/transfer2_fastcut.mp4
