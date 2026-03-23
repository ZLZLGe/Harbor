#!/bin/bash
set -euo pipefail

cat > /opt/syzkaller/sys/linux/dev_capring.txt <<'EOF'
include <linux/types.h>

resource fd_capring[fd]

syz_open_dev$capring(dev ptr[in, string["/dev/capring#"]], id intptr, flags flags[open_flags]) fd_capring

read$capring(fd fd_capring, buf ptr[out, array[int8, 64]], count len[buf])
write$capring(fd fd_capring, buf ptr[in, array[int8, 64]], count len[buf])

ioctl$CAPRING_GET_SLOT(fd fd_capring, cmd const[CAPRING_GET_SLOT], arg ptr[out, int32])
EOF

cat > /opt/syzkaller/sys/linux/dev_capring.txt.const <<'EOF'
arches = amd64, 386

CAPRING_GET_SLOT = 2147771185
CAPRING_ENABLE_TRACE = 25395
EOF

cd /opt/syzkaller
make descriptions
make all
