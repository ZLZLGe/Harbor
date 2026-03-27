#!/bin/bash
set -euo pipefail

ffmpeg -y -v error \
  -i /root/input.mp4 \
  -ss 00:00:02.000 -t 00:00:05.000 \
  -map 0:v:0 -map 0:a:0? \
  -c:v libx264 -preset veryfast -crf 18 -pix_fmt yuv420p \
  -c:a aac -ar 48000 -ac 1 \
  /root/similar_window.mp4
