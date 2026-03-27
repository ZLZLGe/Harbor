#!/bin/bash
set -euo pipefail

ffmpeg -y -loglevel error -i /root/input.mp4 \
  -c:v libvpx-vp9 -b:v 900k \
  -c:a libopus -b:a 96k \
  /root/transfer2_preview.webm

container="$(ffprobe -v error -show_entries format=format_name -of default=nokey=1:noprint_wrappers=1 /root/transfer2_preview.webm)"
video_codec="$(ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of default=nokey=1:noprint_wrappers=1 /root/transfer2_preview.webm)"
audio_codec="$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of default=nokey=1:noprint_wrappers=1 /root/transfer2_preview.webm)"
duration_sec="$(ffprobe -v error -show_entries format=duration -of default=nokey=1:noprint_wrappers=1 /root/transfer2_preview.webm)"
file_size_bytes="$(wc -c < /root/transfer2_preview.webm | awk '{print $1}')"

cat > /root/transfer2_qc.json <<JSON
{
  "container": "$container",
  "video_codec": "$video_codec",
  "audio_codec": "$audio_codec",
  "duration_sec": $duration_sec,
  "file_size_bytes": $file_size_bytes
}
JSON
