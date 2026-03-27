#!/bin/bash
set -euo pipefail

ffmpeg -y -v error \
  -i /root/input.mp4 \
  -ss 00:00:00.000 -t 00:00:04.000 \
  -map 0:v:0 -map 0:a:0? \
  -c:v libx264 -preset veryfast -crf 18 -pix_fmt yuv420p \
  -c:a aac -ar 48000 -ac 1 \
  /tmp/transfer3_head.mp4

ffmpeg -y -v error \
  -i /root/input.mp4 \
  -ss 00:00:06.000 \
  -map 0:v:0 -map 0:a:0? \
  -c:v libx264 -preset veryfast -crf 18 -pix_fmt yuv420p \
  -c:a aac -ar 48000 -ac 1 \
  /tmp/transfer3_tail.mp4

cat > /tmp/transfer3_list.txt <<'LIST'
file '/tmp/transfer3_head.mp4'
file '/tmp/transfer3_tail.mp4'
LIST

ffmpeg -y -v error \
  -f concat -safe 0 -i /tmp/transfer3_list.txt \
  -c copy \
  /root/transfer3_gap_removed.mp4
