#!/bin/bash
set -euo pipefail

ffmpeg -y -loglevel error -i /root/input.mp4 \
  -c:v mpeg4 -q:v 5 \
  -c:a libmp3lame -b:a 192k -ar 44100 -ac 2 \
  /root/transfer3_legacy.avi

container="$(ffprobe -v error -show_entries format=format_name -of default=nokey=1:noprint_wrappers=1 /root/transfer3_legacy.avi)"
video_codec="$(ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of default=nokey=1:noprint_wrappers=1 /root/transfer3_legacy.avi)"
audio_codec="$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of default=nokey=1:noprint_wrappers=1 /root/transfer3_legacy.avi)"
audio_sample_rate_hz="$(ffprobe -v error -select_streams a:0 -show_entries stream=sample_rate -of default=nokey=1:noprint_wrappers=1 /root/transfer3_legacy.avi)"
audio_channels="$(ffprobe -v error -select_streams a:0 -show_entries stream=channels -of default=nokey=1:noprint_wrappers=1 /root/transfer3_legacy.avi)"

cat > /root/transfer3_index.csv <<CSV
file,container,video_codec,audio_codec,audio_sample_rate_hz,audio_channels
transfer3_legacy.avi,$container,$video_codec,$audio_codec,$audio_sample_rate_hz,$audio_channels
CSV
