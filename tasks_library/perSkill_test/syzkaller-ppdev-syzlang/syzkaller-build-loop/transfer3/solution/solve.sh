#!/bin/bash
set -euo pipefail

cat > /opt/syzkaller/sys/linux/dev_bridge_port.txt <<'EOF'
include <linux/if.h>
include <linux/sockios.h>

resource fd_bridgectl[fd]

syz_open_dev$bridgectl(dev ptr[in, string["/dev/bridgectl#"]], id intptr, flags flags[open_flags]) fd_bridgectl

ioctl$BPORT_QUERY_PORT(fd fd_bridgectl, cmd const[BPORT_QUERY_PORT], arg ptr[inout, ifreq_t[int16]])
ioctl$BPORT_GET_INDEX(fd fd_bridgectl, cmd const[BPORT_GET_INDEX], arg ptr[out, int32])
EOF

cat > /opt/syzkaller/sys/linux/dev_bridge_port.txt.const <<'EOF'
arches = amd64, 386

BPORT_QUERY_PORT = 3221381713
BR_PORT_FLOOD = 16
EOF

cd /opt/syzkaller
make descriptions
make all
