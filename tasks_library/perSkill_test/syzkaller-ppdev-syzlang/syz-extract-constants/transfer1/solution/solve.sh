#!/bin/bash
set -euo pipefail

cat > /opt/syzkaller/sys/linux/dev_sensorhub_ctl.txt.const <<'EOF'
arches = amd64, 386

SNS_ENABLE = 29456
SNS_DISABLE = 29457
SNS_GET_SNAPSHOT = 2148168466
SNS_SET_THRESH = 1074295571
SNS_SET_MODE = 1074033428
SENSOR_MODE_IDLE = 0
SENSOR_MODE_FAST = 1
SENSOR_MODE_STREAM = 2
EOF

cd /opt/syzkaller
make descriptions
make all
