#!/bin/bash
set -euo pipefail

mkdir -p /outputs

ffmpeg -y \
  -i /root/program_with_source_subs.mp4 \
  -i /root/channel_watermark.png \
  -filter_complex "[0:v]scale=640:360,boxblur=12:1[bg];[0:v]crop=320:168:0:0,scale=640:300[fg];[bg][fg]overlay=0:0[base];[1:v]scale=150:-1[wm];[base][wm]overlay=460:22[v]" \
  -map "[v]" \
  -map 0:a:0 \
  -c:v libx264 \
  -pix_fmt yuv420p \
  -c:a copy \
  -movflags +faststart \
  /outputs/dubbed-visual-cleanup.mp4
