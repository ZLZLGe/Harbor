#!/bin/bash
set -euo pipefail

mkdir -p /outputs

ffmpeg -y -loglevel error \
  -i /root/input.mp4 \
  -vf "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=720:1280:flags=lanczos,eq=saturation=1.25:contrast=1.05" \
  -c:v libx264 -preset veryfast -crf 22 -pix_fmt yuv420p \
  -c:a aac -b:a 128k -ar 48000 -ac 1 \
  /outputs/transfer1_vertical.mp4
