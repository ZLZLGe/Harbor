Write syzkaller syzlang support for the Linux watchdog character device. In this checkout, `/dev/watchdog*` still needs a dedicated description.

Create:
- /opt/syzkaller/sys/linux/dev_watchdog.txt
- /opt/syzkaller/sys/linux/dev_watchdog.txt.const

In `dev_watchdog.txt`, add:
- `include <linux/watchdog.h>`
- `resource fd_watchdog[fd]`
- a `syz_open_dev` opener for `/dev/watchdog#` that returns `fd_watchdog`
- the core `watchdog_info` struct with `options`, `firmware_version`, and the fixed-size identity buffer
- watchdog ioctl descriptions covering support/status reporting plus timeout and pretimeout management
- flag sets for the watchdog status/support bits and the option bits accepted by `WDIOC_SETOPTIONS`

In `dev_watchdog.txt.const`, add:
- `arches = amd64, 386`
- the ioctl numbers and flag values referenced by your syzlang file

Run these commands to verify your descriptions:
```bash
cd /opt/syzkaller
make descriptions
make all TARGETOS=linux TARGETARCH=amd64
```
