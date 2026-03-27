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

assert '[ -f /root/transfer1_briefing.opus ]' 'transfer1_briefing.opus must exist'
assert '[ -f /root/transfer1_manifest.json ]' 'transfer1_manifest.json must exist'

if [ $status -eq 0 ]; then
  codec="$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of default=nokey=1:noprint_wrappers=1 /root/transfer1_briefing.opus)"
  rate="$(ffprobe -v error -select_streams a:0 -show_entries stream=sample_rate -of default=nokey=1:noprint_wrappers=1 /root/transfer1_briefing.opus)"
  ch="$(ffprobe -v error -select_streams a:0 -show_entries stream=channels -of default=nokey=1:noprint_wrappers=1 /root/transfer1_briefing.opus)"
  src_dur="$(ffprobe -v error -show_entries format=duration -of default=nokey=1:noprint_wrappers=1 /root/input.mp4)"
  out_dur="$(ffprobe -v error -show_entries format=duration -of default=nokey=1:noprint_wrappers=1 /root/transfer1_briefing.opus)"
  diff="$(num_abs_diff "$src_dur" "$out_dur")"

  assert '[ "$codec" = "opus" ]' 'codec must be opus'
  assert '[ "$rate" = "48000" ]' 'sample rate must be 48000'
  assert '[ "$ch" = "1" ]' 'channels must be 1'
  assert "awk -v d='$diff' 'BEGIN { exit !(d<=0.25) }'" 'duration drift must be <= 0.25 sec'

  m_codec="$(sed -n 's/.*"target_audio_codec": *"\([^"]*\)".*/\1/p' /root/transfer1_manifest.json | head -n1)"
  m_rate="$(sed -n 's/.*"target_sample_rate_hz": *\([0-9.]*\).*/\1/p' /root/transfer1_manifest.json | head -n1)"
  m_ch="$(sed -n 's/.*"target_channels": *\([0-9.]*\).*/\1/p' /root/transfer1_manifest.json | head -n1)"
  m_src_dur="$(sed -n 's/.*"source_duration_sec": *\([0-9.]*\).*/\1/p' /root/transfer1_manifest.json | head -n1)"
  m_out_dur="$(sed -n 's/.*"output_duration_sec": *\([0-9.]*\).*/\1/p' /root/transfer1_manifest.json | head -n1)"

  assert '[ "$m_codec" = "$codec" ]' 'manifest codec mismatch'
  assert '[ "$m_rate" = "$rate" ]' 'manifest sample rate mismatch'
  assert '[ "$m_ch" = "$ch" ]' 'manifest channels mismatch'

  md1="$(num_abs_diff "$m_src_dur" "$src_dur")"
  md2="$(num_abs_diff "$m_out_dur" "$out_dur")"
  assert "awk -v d='$md1' 'BEGIN { exit !(d<=0.01) }'" 'manifest source duration mismatch'
  assert "awk -v d='$md2' 'BEGIN { exit !(d<=0.01) }'" 'manifest output duration mismatch'
fi

mkdir -p /logs/verifier
if [ $status -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
exit 0
