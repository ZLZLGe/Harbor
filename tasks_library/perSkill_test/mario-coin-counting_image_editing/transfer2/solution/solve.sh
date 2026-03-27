#!/bin/bash
set -euo pipefail

cd /root
rm -f /root/mario_skill_preview.gif /tmp/frame_*.png

convert /root/coin.png -colorspace Gray -resize 80x80\! /tmp/frame_01.png
convert /root/enemy.png -colorspace Gray -resize 80x80\! /tmp/frame_02.png
convert /root/turtle.png -colorspace Gray -resize 80x80\! /tmp/frame_03.png
convert /root/coin.png -colorspace Gray -negate -resize 80x80\! /tmp/frame_04.png
convert /root/enemy.png -colorspace Gray -edge 1 -resize 80x80\! /tmp/frame_05.png
convert /root/turtle.png -colorspace Gray -blur 0x1 -resize 80x80\! /tmp/frame_06.png

convert -delay 25 -loop 0 \
  /tmp/frame_01.png /tmp/frame_02.png /tmp/frame_03.png \
  /tmp/frame_04.png /tmp/frame_05.png /tmp/frame_06.png \
  /root/mario_skill_preview.gif
