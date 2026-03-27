#!/bin/bash
set -euo pipefail

cd /root
rm -f /root/mario_image_audit.csv /tmp/audit_*.png

convert /root/coin.png -colorspace Gray -resize 48x48\! /tmp/audit_coin.png
convert /root/enemy.png -colorspace Gray -resize 48x48\! -contrast /tmp/audit_enemy.png
convert /root/turtle.png -colorspace Gray -resize 48x48\! -blur 0x1 /tmp/audit_turtle.png

metric_row() {
  local name="$1"
  local file="$2"
  local wh
  local mean
  wh=$(identify -format "%w,%h" "$file")
  mean=$(identify -format "%[fx:mean*255]" "$file")
  python3 - "$name" "$wh" "$mean" << 'PY'
import sys
name = sys.argv[1]
wh = sys.argv[2]
mean = float(sys.argv[3])
print(f"{name},{wh},{mean:.2f}")
PY
}

{
  echo "asset,width,height,mean_gray"
  metric_row "coin" /tmp/audit_coin.png
  metric_row "enemy" /tmp/audit_enemy.png
  metric_row "turtle" /tmp/audit_turtle.png
} > /root/mario_image_audit.csv
