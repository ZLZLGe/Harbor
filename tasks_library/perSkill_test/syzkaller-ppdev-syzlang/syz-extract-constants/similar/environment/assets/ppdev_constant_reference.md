Use manual constants for this task. Kernel source is not available.

Ioctl formulas for ppdev (`type = 'p'`):
- `PPCLAIM = _IO('p', 0x8b)`
- `PPRELEASE = _IO('p', 0x8c)`
- `PPSETMODE = _IOW('p', 0x80, 4)`
- `PPGETMODE = _IOR('p', 0x98, 4)`
- `PPNEGOT = _IOW('p', 0x91, 4)`
- `PPFCONTROL = _IOW('p', 0x8e, 2)`
- `PPSETFLAGS = _IOW('p', 0x9b, 4)`
- `PPGETFLAGS = _IOR('p', 0x9a, 4)`

Literal flag values:
- `IEEE1284_MODE_NIBBLE = 0`
- `IEEE1284_MODE_BYTE = 1`
- `IEEE1284_MODE_COMPAT = 2`
- `IEEE1284_MODE_ECP = 16`
- `PP_FASTWRITE = 4`
- `PP_FASTREAD = 8`
- `PP_W91284PIC = 16`
