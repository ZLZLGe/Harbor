#!/bin/bash
set -euo pipefail

ffmpeg -y -v error \
  -i /root/input.mp4 \
  -ss 00:00:00.000 -t 00:00:03.000 \
  -map 0:v:0 -map 0:a:0? \
  -c:v libx264 -preset veryfast -crf 18 -pix_fmt yuv420p \
  -c:a aac -ar 48000 -ac 1 \
  /tmp/transfer1_part_a.mp4

ffmpeg -y -v error \
  -i /root/input.mp4 \
  -ss 00:00:09.000 -t 00:00:03.000 \
  -map 0:v:0 -map 0:a:0? \
  -c:v libx264 -preset veryfast -crf 18 -pix_fmt yuv420p \
  -c:a aac -ar 48000 -ac 1 \
  /tmp/transfer1_part_b.mp4

cat > /tmp/transfer1_list.txt <<'LIST'
file '/tmp/transfer1_part_a.mp4'
file '/tmp/transfer1_part_b.mp4'
LIST

ffmpeg -y -v error \
  -f concat -safe 0 -i /tmp/transfer1_list.txt \
  -c copy \
  /root/transfer1_highlight.mp4
