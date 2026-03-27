#!/bin/bash
set -euo pipefail

mkdir -p /outputs

ffmpeg -y -loglevel error \
  -i /root/input.mp4 \
  -vf "scale=960:540:flags=lanczos,drawbox=x=iw-220:y=ih-90:w=200:h=70:color=black@0.35:t=fill,drawbox=x=iw-210:y=ih-80:w=180:h=50:color=yellow@0.60:t=fill,gblur=sigma=0.35" \
  -c:v libx264 -preset veryfast -crf 22 -pix_fmt yuv420p \
  -c:a aac -b:a 128k -ar 48000 -ac 1 \
  /outputs/transfer3_watermark_master.mp4
