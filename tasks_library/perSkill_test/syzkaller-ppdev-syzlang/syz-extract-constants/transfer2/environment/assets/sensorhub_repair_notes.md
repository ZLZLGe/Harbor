Repair the constants using these encodings with `type = 'H'`:
- `SHUB_RESET = _IO('H', 0x24)`
- `SHUB_SET_MODE = _IOW('H', 0x21, 4)`
- `SHUB_GET_TEMP = _IOR('H', 0x20, 4)`
- `SHUB_GET_SAMPLE = _IOR('H', 0x22, 8)`
- `SHUB_SET_LIMITS = _IOW('H', 0x23, 8)`

Literal mode values:
- `SHUB_MODE_LOW_POWER = 1`
- `SHUB_MODE_BURST = 2`
- `SHUB_MODE_CALIBRATE = 4`
