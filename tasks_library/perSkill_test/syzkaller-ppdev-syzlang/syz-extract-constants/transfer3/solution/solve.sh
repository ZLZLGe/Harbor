#!/bin/bash
set -euo pipefail

cat > /opt/syzkaller/sys/linux/dev_bridge_port.txt.const <<'EOF'
arches = amd64, 386

BPORT_SET_PORT = 1073898064
BPORT_QUERY_PORT = 3221381713
BPORT_GET_INDEX = 2147770962
BPORT_CLEAR_STATS = 25171
BR_PORT_UP = 1
BR_PORT_LEARNING = 4
BR_PORT_FLOOD = 16
EOF

cd /opt/syzkaller
make descriptions
make all
