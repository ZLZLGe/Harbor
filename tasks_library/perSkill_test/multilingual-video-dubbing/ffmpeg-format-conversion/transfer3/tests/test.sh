#!/bin/bash
set -u

status=0

assert() {
  if ! eval "$1"; then
    echo "ASSERTION FAILED: $2"
    status=1
  fi
}

assert '[ -f /root/transfer3_legacy.avi ]' 'transfer3_legacy.avi must exist'
assert '[ -f /root/transfer3_index.csv ]' 'transfer3_index.csv must exist'

if [ $status -eq 0 ]; then
  container="$(ffprobe -v error -show_entries format=format_name -of default=nokey=1:noprint_wrappers=1 /root/transfer3_legacy.avi)"
  vcodec="$(ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of default=nokey=1:noprint_wrappers=1 /root/transfer3_legacy.avi)"
  acodec="$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of default=nokey=1:noprint_wrappers=1 /root/transfer3_legacy.avi)"
  arate="$(ffprobe -v error -select_streams a:0 -show_entries stream=sample_rate -of default=nokey=1:noprint_wrappers=1 /root/transfer3_legacy.avi)"
  ach="$(ffprobe -v error -select_streams a:0 -show_entries stream=channels -of default=nokey=1:noprint_wrappers=1 /root/transfer3_legacy.avi)"

  assert 'echo "$container" | grep -q avi' 'container must include avi'
  assert '[ "$vcodec" = "mpeg4" ]' 'video codec must be mpeg4'
  assert '[ "$acodec" = "mp3" ]' 'audio codec must be mp3'
  assert '[ "$arate" = "44100" ]' 'audio sample rate must be 44100'
  assert '[ "$ach" = "2" ]' 'audio channels must be 2'

  line_count="$(wc -l < /root/transfer3_index.csv | awk '{print $1}')"
  header="$(sed -n '1p' /root/transfer3_index.csv)"
  row="$(sed -n '2p' /root/transfer3_index.csv)"
  expected_row="transfer3_legacy.avi,$container,$vcodec,$acodec,$arate,$ach"

  assert '[ "$line_count" = "2" ]' 'csv must have exactly 2 lines'
  assert '[ "$header" = "file,container,video_codec,audio_codec,audio_sample_rate_hz,audio_channels" ]' 'csv header mismatch'
  assert '[ "$row" = "$expected_row" ]' 'csv data row mismatch'
fi

mkdir -p /logs/verifier
if [ $status -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
exit 0
