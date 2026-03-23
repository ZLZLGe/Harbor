Manual constants only. Do not rely on kernel source.

Use `type = 'L'` and these ioctl encodings:
- `LABPULSE_ARM = _IO('L', 0x01)`
- `LABPULSE_SET_RATE = _IOW('L', 0x02, 4)`
- `LABPULSE_GET_RATE = _IOR('L', 0x03, 4)`
- `LABPULSE_SET_WINDOW = _IOW('L', 0x04, 4)`
- `LABPULSE_GET_STATUS = _IOR('L', 0x05, 4)`
- `LABPULSE_SET_FLAGS = _IOW('L', 0x06, 4)`

Literal flags:
- `LABPULSE_FLAG_EDGE = 1`
- `LABPULSE_FLAG_LEVEL = 2`
- `LABPULSE_FLAG_DIAG = 4`
