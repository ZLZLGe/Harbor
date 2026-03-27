#!/bin/bash
set -euo pipefail

ffmpeg -y -loglevel error -i /root/input.mp4 -vn -c:a libopus -b:a 96k -ar 48000 -ac 1 /root/transfer1_briefing.opus

source_container="$(ffprobe -v error -show_entries format=format_name -of default=nokey=1:noprint_wrappers=1 /root/input.mp4)"
target_audio_codec="$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of default=nokey=1:noprint_wrappers=1 /root/transfer1_briefing.opus)"
target_sample_rate_hz="$(ffprobe -v error -select_streams a:0 -show_entries stream=sample_rate -of default=nokey=1:noprint_wrappers=1 /root/transfer1_briefing.opus)"
target_channels="$(ffprobe -v error -select_streams a:0 -show_entries stream=channels -of default=nokey=1:noprint_wrappers=1 /root/transfer1_briefing.opus)"
source_duration_sec="$(ffprobe -v error -show_entries format=duration -of default=nokey=1:noprint_wrappers=1 /root/input.mp4)"
output_duration_sec="$(ffprobe -v error -show_entries format=duration -of default=nokey=1:noprint_wrappers=1 /root/transfer1_briefing.opus)"

cat > /root/transfer1_manifest.json <<JSON
{
  "source_container": "$source_container",
  "target_audio_codec": "$target_audio_codec",
  "target_sample_rate_hz": $target_sample_rate_hz,
  "target_channels": $target_channels,
  "source_duration_sec": $source_duration_sec,
  "output_duration_sec": $output_duration_sec
}
JSON
