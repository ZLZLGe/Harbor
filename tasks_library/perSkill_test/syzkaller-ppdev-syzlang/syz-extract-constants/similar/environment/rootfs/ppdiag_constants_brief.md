# Parallel Diagnostics Constants

Create `/opt/syzkaller/sys/linux/dev_ppdiag.txt.const` for the existing description file.

Use:

- `arches = amd64, 386`
- ioctl formulas:
  - `_IO(type, nr) = (type << 8) | nr`
  - `_IOR(type, nr, size) = (2 << 30) | (size << 16) | (type << 8) | nr`
  - `_IOW(type, nr, size) = (1 << 30) | (size << 16) | (type << 8) | nr`
- type character: `'p'`

Required constants:

- `PPDIAG_CLAIM = _IO('p', 0x40)`
- `PPDIAG_RELEASE = _IO('p', 0x41)`
- `PPDIAG_GETMODE = _IOR('p', 0x42, 4)`
- `PPDIAG_SETMODE = _IOW('p', 0x43, 4)`
- `PPDIAG_READ_STATUS = _IOR('p', 0x44, 1)`
- `PPDIAG_WRITE_CTRL = _IOW('p', 0x45, 1)`
- `PPDIAG_FROB = _IOW('p', 0x46, 2)`
- `PPDIAG_MODE_COMPAT = 1`
- `PPDIAG_MODE_ECP = 16`
- `PPDIAG_MODE_EPP = 256`
