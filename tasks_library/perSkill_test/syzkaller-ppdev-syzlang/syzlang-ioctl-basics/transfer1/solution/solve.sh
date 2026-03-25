#!/bin/bash
set -euo pipefail

cat > /opt/syzkaller/sys/linux/dev_sensorhub_ctl.txt <<'EOF'
include <linux/types.h>

resource fd_sensorhub[fd]

sensor_threshold {
	channel	int16
	limit	int32
	hysteresis	int16
}

sensor_snapshot {
	ambient	int32
	surface	int32
	humidity	int16
}

sensor_modes = SENSOR_MODE_IDLE, SENSOR_MODE_FAST, SENSOR_MODE_STREAM

syz_open_dev$sensorhub(dev ptr[in, string["/dev/sensorhub#"]], id intptr, flags flags[open_flags]) fd_sensorhub

ioctl$SNS_ENABLE(fd fd_sensorhub, cmd const[SNS_ENABLE])
ioctl$SNS_DISABLE(fd fd_sensorhub, cmd const[SNS_DISABLE])
ioctl$SNS_GET_SNAPSHOT(fd fd_sensorhub, cmd const[SNS_GET_SNAPSHOT], arg ptr[out, sensor_snapshot])
ioctl$SNS_SET_THRESH(fd fd_sensorhub, cmd const[SNS_SET_THRESH], arg ptr[in, sensor_threshold])
ioctl$SNS_SET_MODE(fd fd_sensorhub, cmd const[SNS_SET_MODE], arg ptr[in, flags[sensor_modes, int32]])
EOF

cd /opt/syzkaller
make descriptions
make all
