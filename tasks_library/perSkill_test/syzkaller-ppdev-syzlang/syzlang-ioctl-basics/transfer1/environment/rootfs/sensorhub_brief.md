# Sensor Hub Control Interface

Create `/opt/syzkaller/sys/linux/dev_sensorhub_ctl.txt`.

Required elements:

- `include <linux/types.h>`
- `resource fd_sensorhub[fd]`
- `syz_open_dev$sensorhub(dev ptr[in, string["/dev/sensorhub#"]], id intptr, flags flags[open_flags]) fd_sensorhub`

Structs:

```text
sensor_threshold {
    channel     int16
    limit       int32
    hysteresis  int16
}

sensor_snapshot {
    ambient     int32
    surface     int32
    humidity    int16
}
```

Flag set:

```text
sensor_modes = SENSOR_MODE_IDLE, SENSOR_MODE_FAST, SENSOR_MODE_STREAM
```

Ioctls:

- `SNS_ENABLE`: no data argument
- `SNS_DISABLE`: no data argument
- `SNS_GET_SNAPSHOT`: `ptr[out, sensor_snapshot]`
- `SNS_SET_THRESH`: `ptr[in, sensor_threshold]`
- `SNS_SET_MODE`: `ptr[in, flags[sensor_modes, int32]]`
