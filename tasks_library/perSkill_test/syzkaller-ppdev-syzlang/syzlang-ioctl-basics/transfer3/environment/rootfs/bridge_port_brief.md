# Bridge Port Control Interface

Create `/opt/syzkaller/sys/linux/dev_bridge_port.txt`.

Required elements:

- `include <linux/if.h>`
- `include <linux/sockios.h>`
- `resource fd_bridgectl[fd]`
- `syz_open_dev$bridgectl(dev ptr[in, string["/dev/bridgectl#"]], id intptr, flags flags[open_flags]) fd_bridgectl`

Flag set:

```text
bridge_flags = BR_PORT_UP, BR_PORT_LEARNING, BR_PORT_FLOOD
```

Ioctls:

- `BPORT_SET_PORT`: `ptr[in, ifreq_t[flags[bridge_flags, int16]]]`
- `BPORT_QUERY_PORT`: `ptr[inout, ifreq_t[int16]]`
- `BPORT_GET_INDEX`: `ptr[out, int32]`
