#!/bin/bash
set -euo pipefail

mkdir -p /outputs

ffmpeg -y -v error \
  -i /root/ivr_prompt_master.wav \
  -ar 8000 \
  -ac 1 \
  -c:a pcm_mulaw \
  /outputs/ivr_prompt.wav
