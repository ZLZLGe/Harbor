#!/bin/bash
set -euo pipefail

mkdir -p /outputs

ffmpeg -y \
  -i /root/lesson_clip.mp4 \
  -i /root/aligned_narration.wav \
  -map 0:v:0 \
  -map 1:a:0 \
  -c:v libx264 \
  -preset medium \
  -crf 18 \
  -pix_fmt yuv420p \
  -c:a aac \
  -b:a 128k \
  -ar 48000 \
  -ac 1 \
  -movflags +faststart \
  /outputs/localized_lesson.mp4
