#!/bin/bash
set -euo pipefail

cat > /root/transfer1_cue_sheet.csv <<'EOF'
cue_title,start_seconds,end_seconds,duration_seconds
Tracing inner walls,0,73,73
Break,73,78,5
Continue tracing inner walls,78,314,236
Remove doubled vertices,314,325,11
Save,325,331,6
EOF
