#!/bin/bash
set -euo pipefail

cat > /opt/syzkaller/sys/linux/dev_bridge_port.txt <<'EOF'
include <linux/if.h>
include <linux/sockios.h>

resource fd_bridgectl[fd]

bridge_flags = BR_PORT_UP, BR_PORT_LEARNING, BR_PORT_FLOOD

syz_open_dev$bridgectl(dev ptr[in, string["/dev/bridgectl#"]], id intptr, flags flags[open_flags]) fd_bridgectl

ioctl$BPORT_SET_PORT(fd fd_bridgectl, cmd const[BPORT_SET_PORT], arg ptr[in, ifreq_t[flags[bridge_flags, int16]]])
ioctl$BPORT_QUERY_PORT(fd fd_bridgectl, cmd const[BPORT_QUERY_PORT], arg ptr[inout, ifreq_t[int16]])
ioctl$BPORT_GET_INDEX(fd fd_bridgectl, cmd const[BPORT_GET_INDEX], arg ptr[out, int32])
EOF

cd /opt/syzkaller
make descriptions
make all
