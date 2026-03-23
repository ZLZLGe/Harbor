Use manual constants with `type = 'R'`.

Encodings:
- `CAMRELAY_ATTACH = _IO('R', 0x30)`
- `CAMRELAY_DETACH = _IO('R', 0x31)`
- `CAMRELAY_SET_ROUTE = _IOW('R', 0x32, 4)`
- `CAMRELAY_GET_ROUTE = _IOR('R', 0x33, 4)`
- `CAMRELAY_SWAP_ROUTE = _IOWR('R', 0x34, 8)`
- `CAMRELAY_SET_FLAGS = _IOW('R', 0x35, 4)`

Literal flags:
- `CAMRELAY_FLAG_SAFE = 1`
- `CAMRELAY_FLAG_FORCE = 2`
- `CAMRELAY_FLAG_TRACE = 4`
