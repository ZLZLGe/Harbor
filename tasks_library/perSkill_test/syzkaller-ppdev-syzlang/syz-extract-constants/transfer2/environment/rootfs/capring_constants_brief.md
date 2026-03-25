# Capture Ring Constants

Create `/opt/syzkaller/sys/linux/dev_capring.txt.const`.

Use:

- `arches = amd64, 386`
- ioctl formulas:
  - `_IO(type, nr) = (type << 8) | nr`
  - `_IOR(type, nr, size) = (2 << 30) | (size << 16) | (type << 8) | nr`
  - `_IOW(type, nr, size) = (1 << 30) | (size << 16) | (type << 8) | nr`
- type character: `'c'`

Required constants:

- `CAPRING_SET_SLOT = _IOW('c', 0x30, 4)`
- `CAPRING_GET_SLOT = _IOR('c', 0x31, 4)`
- `CAPRING_SUBMIT = _IOW('c', 0x32, 8)`
- `CAPRING_ENABLE_TRACE = _IO('c', 0x33)`
- `CAPRING_TRACE_BURST = 1`
- `CAPRING_TRACE_LOSSY = 2`
