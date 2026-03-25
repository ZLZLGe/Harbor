# Bridge Port Constants

Create `/opt/syzkaller/sys/linux/dev_bridge_port.txt.const`.

Use:

- `arches = amd64, 386`
- ioctl formulas:
  - `_IO(type, nr) = (type << 8) | nr`
  - `_IOR(type, nr, size) = (2 << 30) | (size << 16) | (type << 8) | nr`
  - `_IOW(type, nr, size) = (1 << 30) | (size << 16) | (type << 8) | nr`
  - `_IOWR(type, nr, size) = (3 << 30) | (size << 16) | (type << 8) | nr`
- type character: `'b'`

Required constants:

- `BPORT_SET_PORT = _IOW('b', 0x50, 2)`
- `BPORT_QUERY_PORT = _IOWR('b', 0x51, 2)`
- `BPORT_GET_INDEX = _IOR('b', 0x52, 4)`
- `BPORT_CLEAR_STATS = _IO('b', 0x53)`
- `BR_PORT_UP = 1`
- `BR_PORT_LEARNING = 4`
- `BR_PORT_FLOOD = 16`
