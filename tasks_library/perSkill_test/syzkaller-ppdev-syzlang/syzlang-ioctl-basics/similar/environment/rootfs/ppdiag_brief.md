# Parallel Port Diagnostics Interface

Create a syzlang description file at `/opt/syzkaller/sys/linux/dev_ppdiag.txt`.

Required elements:

- `include <linux/ppdev.h>`
- `include <linux/parport.h>`
- `resource fd_ppdiag[fd]`
- `syz_open_dev$ppdiag(dev ptr[in, string["/dev/parport#"]], id intptr, flags flags[open_flags]) fd_ppdiag`

Define this struct:

```text
ppdiag_window {
    mask     int8
    value    int8
}
```

Define this flag set:

```text
ppdiag_modes = PPDIAG_MODE_COMPAT, PPDIAG_MODE_ECP, PPDIAG_MODE_EPP
```

Add these ioctl descriptions:

- `PPDIAG_CLAIM`: no data argument
- `PPDIAG_RELEASE`: no data argument
- `PPDIAG_GETMODE`: `ptr[out, int32]`
- `PPDIAG_SETMODE`: `ptr[in, flags[ppdiag_modes, int32]]`
- `PPDIAG_READ_STATUS`: `ptr[out, int8]`
- `PPDIAG_WRITE_CTRL`: `ptr[in, int8]`
- `PPDIAG_FROB`: `ptr[in, ppdiag_window]`
