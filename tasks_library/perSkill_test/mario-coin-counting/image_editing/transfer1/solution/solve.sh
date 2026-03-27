#!/bin/bash
set -euo pipefail

cd /root
rm -f /root/mario_icon_atlas.png /tmp/coin_norm.png /tmp/enemy_norm.png /tmp/turtle_norm.png

convert /root/coin.png -colorspace Gray -resize 64x64\! /tmp/coin_norm.png
convert /root/enemy.png -colorspace Gray -flip -resize 64x64\! /tmp/enemy_norm.png
convert /root/turtle.png -colorspace Gray -flop -resize 64x64\! /tmp/turtle_norm.png

convert /tmp/coin_norm.png /tmp/enemy_norm.png /tmp/turtle_norm.png +append /root/mario_icon_atlas.png
