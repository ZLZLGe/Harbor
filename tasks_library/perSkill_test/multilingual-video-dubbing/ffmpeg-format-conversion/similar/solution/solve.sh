#!/bin/bash
set -euo pipefail

ffmpeg -y -loglevel error -i /root/input.mp4 -c copy /root/similar_master.mkv
ffmpeg -y -loglevel error -i /root/input.mp4 -vn -c:a aac -b:a 128k -ar 48000 -ac 1 /root/similar_audio.aac

src_video_codec="$(ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of default=nokey=1:noprint_wrappers=1 /root/input.mp4)"
src_audio_codec="$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of default=nokey=1:noprint_wrappers=1 /root/input.mp4)"
mkv_container="$(ffprobe -v error -show_entries format=format_name -of default=nokey=1:noprint_wrappers=1 /root/similar_master.mkv)"
mkv_duration_sec="$(ffprobe -v error -show_entries format=duration -of default=nokey=1:noprint_wrappers=1 /root/similar_master.mkv)"
aac_codec="$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of default=nokey=1:noprint_wrappers=1 /root/similar_audio.aac)"
aac_sample_rate_hz="$(ffprobe -v error -select_streams a:0 -show_entries stream=sample_rate -of default=nokey=1:noprint_wrappers=1 /root/similar_audio.aac)"
aac_channels="$(ffprobe -v error -select_streams a:0 -show_entries stream=channels -of default=nokey=1:noprint_wrappers=1 /root/similar_audio.aac)"

cat > /root/similar_report.json <<JSON
{
  "source_video_codec": "$src_video_codec",
  "source_audio_codec": "$src_audio_codec",
  "mkv_container": "$mkv_container",
  "mkv_duration_sec": $mkv_duration_sec,
  "aac_codec": "$aac_codec",
  "aac_sample_rate_hz": $aac_sample_rate_hz,
  "aac_channels": $aac_channels
}
JSON
