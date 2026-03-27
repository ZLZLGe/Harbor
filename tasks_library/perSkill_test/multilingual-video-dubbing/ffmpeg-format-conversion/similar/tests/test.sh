#!/bin/bash
set -u

status=0

assert() {
  if ! eval "$1"; then
    echo "ASSERTION FAILED: $2"
    status=1
  fi
}

num_abs_diff() {
  awk -v a="$1" -v b="$2" 'BEGIN { d=a-b; if (d<0) d=-d; print d }'
}

assert '[ -f /root/similar_master.mkv ]' 'similar_master.mkv must exist'
assert '[ -f /root/similar_audio.aac ]' 'similar_audio.aac must exist'
assert '[ -f /root/similar_report.json ]' 'similar_report.json must exist'

if [ $status -eq 0 ]; then
  src_video_codec="$(ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of default=nokey=1:noprint_wrappers=1 /root/input.mp4)"
  src_audio_codec="$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of default=nokey=1:noprint_wrappers=1 /root/input.mp4)"
  mkv_video_codec="$(ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of default=nokey=1:noprint_wrappers=1 /root/similar_master.mkv)"
  mkv_audio_codec="$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of default=nokey=1:noprint_wrappers=1 /root/similar_master.mkv)"
  mkv_container="$(ffprobe -v error -show_entries format=format_name -of default=nokey=1:noprint_wrappers=1 /root/similar_master.mkv)"
  src_duration="$(ffprobe -v error -show_entries format=duration -of default=nokey=1:noprint_wrappers=1 /root/input.mp4)"
  mkv_duration="$(ffprobe -v error -show_entries format=duration -of default=nokey=1:noprint_wrappers=1 /root/similar_master.mkv)"
  aac_codec="$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of default=nokey=1:noprint_wrappers=1 /root/similar_audio.aac)"
  aac_rate="$(ffprobe -v error -select_streams a:0 -show_entries stream=sample_rate -of default=nokey=1:noprint_wrappers=1 /root/similar_audio.aac)"
  aac_channels="$(ffprobe -v error -select_streams a:0 -show_entries stream=channels -of default=nokey=1:noprint_wrappers=1 /root/similar_audio.aac)"

  assert 'echo "$mkv_container" | grep -q matroska' 'container must include matroska'
  assert '[ "$mkv_video_codec" = "$src_video_codec" ]' 'video codec must be copied'
  assert '[ "$mkv_audio_codec" = "$src_audio_codec" ]' 'audio codec must be copied'

  duration_diff="$(num_abs_diff "$src_duration" "$mkv_duration")"
  assert "awk -v d='$duration_diff' 'BEGIN { exit !(d<=0.20) }'" 'duration drift must be <= 0.20 sec'

  assert '[ "$aac_codec" = "aac" ]' 'sidecar codec must be aac'
  assert '[ "$aac_rate" = "48000" ]' 'sidecar rate must be 48000'
  assert '[ "$aac_channels" = "1" ]' 'sidecar channels must be mono'

  report_dur="$(sed -n 's/.*"mkv_duration_sec": *\([0-9.]*\).*/\1/p' /root/similar_report.json | head -n1)"
  assert 'grep -q "\"source_video_codec\": \"'$src_video_codec'\"" /root/similar_report.json' 'report source_video_codec mismatch'
  assert 'grep -q "\"source_audio_codec\": \"'$src_audio_codec'\"" /root/similar_report.json' 'report source_audio_codec mismatch'
  assert 'grep -q "\"aac_codec\": \"aac\"" /root/similar_report.json' 'report aac_codec mismatch'
  assert 'grep -q "\"aac_sample_rate_hz\": 48000" /root/similar_report.json' 'report sample rate mismatch'
  assert 'grep -q "\"aac_channels\": 1" /root/similar_report.json' 'report channels mismatch'
  report_diff="$(num_abs_diff "$report_dur" "$mkv_duration")"
  assert "awk -v d='$report_diff' 'BEGIN { exit !(d<=0.05) }'" 'report duration mismatch'
fi

mkdir -p /logs/verifier
if [ $status -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
exit 0
