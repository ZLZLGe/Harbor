#!/bin/bash
set -euo pipefail

cat > /root/transfer2_stage_windows.md <<'EOF'
# Stage Windows

| stage_key | label | start_seconds | end_seconds |
| --- | --- | ---: | ---: |
| cleanup | Remove unnecessary geometry | 0 | 42 |
| faces | Make the floor's faces | 42 | 53 |
| background | Make the background | 53 | 99 |
| extrude_z | Extruding the walls in Z | 99 | 115 |
| orientation_review | Reviewing face orientation | 115 | 154 |
| wall_thickness_modifiers | Adding thickness to walls with Modifiers | 154 | 193 |
EOF
