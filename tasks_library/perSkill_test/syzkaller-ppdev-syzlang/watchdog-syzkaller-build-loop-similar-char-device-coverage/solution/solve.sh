#!/bin/bash
set -e

cd /opt/syzkaller/sys/linux

cat <<'EOF' > dev_watchdog.txt
# Syzkaller descriptions for Linux watchdog devices

include <linux/watchdog.h>

resource fd_watchdog[fd]

watchdog_info {
	options				flags[watchdog_option_flags, int32]
	firmware_version	int32
	identity			array[int8, 32]
}

watchdog_option_flags = WDIOF_OVERHEAT, WDIOF_FANFAULT, WDIOF_EXTERN1, WDIOF_EXTERN2, WDIOF_POWERUNDER, WDIOF_CARDRESET, WDIOF_POWEROVER, WDIOF_SETTIMEOUT, WDIOF_MAGICCLOSE, WDIOF_PRETIMEOUT, WDIOF_ALARMONLY, WDIOF_KEEPALIVEPING
watchdog_setoptions = WDIOS_DISABLECARD, WDIOS_ENABLECARD, WDIOS_TEMPPANIC

syz_open_dev$watchdog(dev ptr[in, string["/dev/watchdog#"]], id intptr, flags flags[open_flags]) fd_watchdog

ioctl$WDIOC_GETSUPPORT(fd fd_watchdog, cmd const[WDIOC_GETSUPPORT], arg ptr[out, watchdog_info])
ioctl$WDIOC_GETSTATUS(fd fd_watchdog, cmd const[WDIOC_GETSTATUS], arg ptr[out, flags[watchdog_option_flags, int32]])
ioctl$WDIOC_GETBOOTSTATUS(fd fd_watchdog, cmd const[WDIOC_GETBOOTSTATUS], arg ptr[out, flags[watchdog_option_flags, int32]])
ioctl$WDIOC_SETOPTIONS(fd fd_watchdog, cmd const[WDIOC_SETOPTIONS], arg ptr[in, flags[watchdog_setoptions, int32]])
ioctl$WDIOC_SETTIMEOUT(fd fd_watchdog, cmd const[WDIOC_SETTIMEOUT], arg ptr[inout, int32])
ioctl$WDIOC_GETTIMEOUT(fd fd_watchdog, cmd const[WDIOC_GETTIMEOUT], arg ptr[out, int32])
ioctl$WDIOC_SETPRETIMEOUT(fd fd_watchdog, cmd const[WDIOC_SETPRETIMEOUT], arg ptr[inout, int32])
ioctl$WDIOC_GETPRETIMEOUT(fd fd_watchdog, cmd const[WDIOC_GETPRETIMEOUT], arg ptr[out, int32])
ioctl$WDIOC_GETTIMELEFT(fd fd_watchdog, cmd const[WDIOC_GETTIMELEFT], arg ptr[out, int32])
EOF

cat <<'EOF' > dev_watchdog.txt.const
# Arch-specific constants for Linux watchdog syzlang descriptions
arches = amd64, 386

WDIOC_GETSUPPORT = 2150127360
WDIOC_GETSTATUS = 2147768065
WDIOC_GETBOOTSTATUS = 2147768066
WDIOC_SETOPTIONS = 2147768068
WDIOC_SETTIMEOUT = 3221509894
WDIOC_GETTIMEOUT = 2147768071
WDIOC_SETPRETIMEOUT = 3221509896
WDIOC_GETPRETIMEOUT = 2147768073
WDIOC_GETTIMELEFT = 2147768074

WDIOF_OVERHEAT = 1
WDIOF_FANFAULT = 2
WDIOF_EXTERN1 = 4
WDIOF_EXTERN2 = 8
WDIOF_POWERUNDER = 16
WDIOF_CARDRESET = 32
WDIOF_POWEROVER = 64
WDIOF_SETTIMEOUT = 128
WDIOF_MAGICCLOSE = 256
WDIOF_PRETIMEOUT = 512
WDIOF_ALARMONLY = 1024
WDIOF_KEEPALIVEPING = 32768

WDIOS_DISABLECARD = 1
WDIOS_ENABLECARD = 2
WDIOS_TEMPPANIC = 4
EOF

cd /opt/syzkaller
make descriptions
make all TARGETOS=linux TARGETARCH=amd64
