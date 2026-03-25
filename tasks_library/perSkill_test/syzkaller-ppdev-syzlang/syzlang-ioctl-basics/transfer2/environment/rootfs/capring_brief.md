# Capture Ring Streaming Interface

Create `/opt/syzkaller/sys/linux/dev_capring.txt`.

Required elements:

- `include <linux/types.h>`
- `resource fd_capring[fd]`
- `syz_open_dev$capring(dev ptr[in, string["/dev/capring#"]], id intptr, flags flags[open_flags]) fd_capring`

Struct:

```text
capring_frame {
    frame_id    int32
    slot        int16
    priority    int16
}
```

Add these specialized syscalls:

- `read$capring(fd fd_capring, buf ptr[out, array[int8, 64]], count len[buf])`
- `write$capring(fd fd_capring, buf ptr[in, array[int8, 64]], count len[buf])`

Add these ioctls:

- `CAPRING_SET_SLOT`: `ptr[in, int32]`
- `CAPRING_GET_SLOT`: `ptr[out, int32]`
- `CAPRING_SUBMIT`: `ptr[in, capring_frame]`
