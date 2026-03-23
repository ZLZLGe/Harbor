# Sensor Hub Constants

Create `/opt/syzkaller/sys/linux/dev_sensorhub_ctl.txt.const`.

Use:

- `arches = amd64, 386`
- ioctl formulas:
  - `_IO(type, nr) = (type << 8) | nr`
  - `_IOR(type, nr, size) = (2 << 30) | (size << 16) | (type << 8) | nr`
  - `_IOW(type, nr, size) = (1 << 30) | (size << 16) | (type << 8) | nr`
- type character: `'s'`

Required constants:

- `SNS_ENABLE = _IO('s', 0x10)`
- `SNS_DISABLE = _IO('s', 0x11)`
- `SNS_GET_SNAPSHOT = _IOR('s', 0x12, 10)`
- `SNS_SET_THRESH = _IOW('s', 0x13, 8)`
- `SNS_SET_MODE = _IOW('s', 0x14, 4)`
- `SENSOR_MODE_IDLE = 0`
- `SENSOR_MODE_FAST = 1`
- `SENSOR_MODE_STREAM = 2`
