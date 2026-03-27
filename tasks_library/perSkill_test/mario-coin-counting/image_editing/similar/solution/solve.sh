#!/bin/bash
set -euo pipefail

cd /root
rm -f /root/mario_keyframe_strip.png /tmp/sim_panel_*.png

convert /root/coin.png -colorspace Gray -resize 64x64\! /tmp/sim_panel_01.png
convert /root/enemy.png -colorspace Gray -resize 64x64\! /tmp/sim_panel_02.png
convert /root/turtle.png -colorspace Gray -resize 64x64\! /tmp/sim_panel_03.png
convert /root/coin.png -colorspace Gray -negate -resize 64x64\! /tmp/sim_panel_04.png

convert /tmp/sim_panel_01.png /tmp/sim_panel_02.png /tmp/sim_panel_03.png /tmp/sim_panel_04.png +append /root/mario_keyframe_strip.png
