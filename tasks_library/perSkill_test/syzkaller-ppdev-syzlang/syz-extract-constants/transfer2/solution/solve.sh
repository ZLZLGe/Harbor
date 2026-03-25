#!/bin/bash
set -euo pipefail

cat > /opt/syzkaller/sys/linux/dev_capring.txt.const <<'EOF'
arches = amd64, 386

CAPRING_SET_SLOT = 1074029360
CAPRING_GET_SLOT = 2147771185
CAPRING_SUBMIT = 1074291506
CAPRING_ENABLE_TRACE = 25395
CAPRING_TRACE_BURST = 1
CAPRING_TRACE_LOSSY = 2
EOF

cd /opt/syzkaller
make descriptions
make all
