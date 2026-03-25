#!/bin/bash
set -euo pipefail

cat > /opt/syzkaller/sys/linux/dev_capring.txt <<'EOF'
include <linux/types.h>

resource fd_capring[fd]

capring_frame {
	frame_id	int32
	slot	int16
	priority	int16
}

syz_open_dev$capring(dev ptr[in, string["/dev/capring#"]], id intptr, flags flags[open_flags]) fd_capring

read$capring(fd fd_capring, buf ptr[out, array[int8, 64]], count len[buf])
write$capring(fd fd_capring, buf ptr[in, array[int8, 64]], count len[buf])

ioctl$CAPRING_SET_SLOT(fd fd_capring, cmd const[CAPRING_SET_SLOT], arg ptr[in, int32])
ioctl$CAPRING_GET_SLOT(fd fd_capring, cmd const[CAPRING_GET_SLOT], arg ptr[out, int32])
ioctl$CAPRING_SUBMIT(fd fd_capring, cmd const[CAPRING_SUBMIT], arg ptr[in, capring_frame])
EOF

cd /opt/syzkaller
make descriptions
make all
