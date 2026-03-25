#!/bin/bash
set -euo pipefail

cat > /root/transfer3_closeout_schedule.tsv <<'EOF'
card_id	label	start_seconds	seconds_until_next
face_orientation_note	Note on face orientation	0	39
save_as	Save As	39	25
mixed_wall_types	If you need thick and thin walls	64	17
great_job	Great job!	81	15
EOF
