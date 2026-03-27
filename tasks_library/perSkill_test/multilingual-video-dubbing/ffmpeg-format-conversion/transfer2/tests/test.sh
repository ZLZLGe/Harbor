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

assert '[ -f /root/transfer2_preview.webm ]' 'transfer2_preview.webm must exist'
assert '[ -f /root/transfer2_qc.json ]' 'transfer2_qc.json must exist'

if [ $status -eq 0 ]; then
  container="$(ffprobe -v error -show_entries format=format_name -of default=nokey=1:noprint_wrappers=1 /root/transfer2_preview.webm)"
  vcodec="$(ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of default=nokey=1:noprint_wrappers=1 /root/transfer2_preview.webm)"
  acodec="$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of default=nokey=1:noprint_wrappers=1 /root/transfer2_preview.webm)"
  src_dur="$(ffprobe -v error -show_entries format=duration -of default=nokey=1:noprint_wrappers=1 /root/input.mp4)"
  out_dur="$(ffprobe -v error -show_entries format=duration -of default=nokey=1:noprint_wrappers=1 /root/transfer2_preview.webm)"
  diff="$(num_abs_diff "$src_dur" "$out_dur")"
  size="$(wc -c < /root/transfer2_preview.webm | awk '{print $1}')"

  assert 'echo "$container" | grep -q webm' 'container must include webm'
  assert '[ "$vcodec" = "vp9" ]' 'video codec must be vp9'
  assert '[ "$acodec" = "opus" ]' 'audio codec must be opus'
  assert "awk -v d='$diff' 'BEGIN { exit !(d<=0.30) }'" 'duration drift must be <= 0.30 sec'
  assert "awk -v s='$size' 'BEGIN { exit !(s>0) }'" 'output size must be > 0'

  q_vcodec="$(sed -n 's/.*"video_codec": *"\([^"]*\)".*/\1/p' /root/transfer2_qc.json | head -n1)"
  q_acodec="$(sed -n 's/.*"audio_codec": *"\([^"]*\)".*/\1/p' /root/transfer2_qc.json | head -n1)"
  q_dur="$(sed -n 's/.*"duration_sec": *\([0-9.]*\).*/\1/p' /root/transfer2_qc.json | head -n1)"
  q_size="$(sed -n 's/.*"file_size_bytes": *\([0-9.]*\).*/\1/p' /root/transfer2_qc.json | head -n1)"

  qdiff="$(num_abs_diff "$q_dur" "$out_dur")"
  assert '[ "$q_vcodec" = "$vcodec" ]' 'qc video codec mismatch'
  assert '[ "$q_acodec" = "$acodec" ]' 'qc audio codec mismatch'
  assert "awk -v d='$qdiff' 'BEGIN { exit !(d<=0.01) }'" 'qc duration mismatch'
  assert '[ "$q_size" = "$size" ]' 'qc size mismatch'
fi

mkdir -p /logs/verifier
if [ $status -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
exit 0
