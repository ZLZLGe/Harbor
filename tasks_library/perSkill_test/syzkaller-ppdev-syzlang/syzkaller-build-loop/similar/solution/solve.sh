#!/bin/bash
set -euo pipefail

cat > /opt/syzkaller/sys/linux/dev_ppdiag.txt <<'EOF'
include <linux/ppdev.h>
include <linux/parport.h>

resource fd_ppdiag[fd]

ppdiag_window {
	mask	int8
	value	int8
}

ppdiag_modes = PPDIAG_MODE_COMPAT, PPDIAG_MODE_ECP, PPDIAG_MODE_EPP

syz_open_dev$ppdiag(dev ptr[in, string["/dev/parport#"]], id intptr, flags flags[open_flags]) fd_ppdiag

ioctl$PPDIAG_CLAIM(fd fd_ppdiag, cmd const[PPDIAG_CLAIM])
ioctl$PPDIAG_RELEASE(fd fd_ppdiag, cmd const[PPDIAG_RELEASE])
ioctl$PPDIAG_GETMODE(fd fd_ppdiag, cmd const[PPDIAG_GETMODE], arg ptr[out, int32])
ioctl$PPDIAG_SETMODE(fd fd_ppdiag, cmd const[PPDIAG_SETMODE], arg ptr[in, flags[ppdiag_modes, int32]])
ioctl$PPDIAG_FROB(fd fd_ppdiag, cmd const[PPDIAG_FROB], arg ptr[in, ppdiag_window])
EOF

cat > /opt/syzkaller/sys/linux/dev_ppdiag.txt.const <<'EOF'
arches = amd64, 386

PPDIAG_CLAIM = 28736
PPDIAG_RELEASE = 28737
PPDIAG_GETMODE = 2147774530
PPDIAG_SETMODE = 1074032707
PPDIAG_FROB = 1073901638
EOF

cd /opt/syzkaller
make descriptions
make all
