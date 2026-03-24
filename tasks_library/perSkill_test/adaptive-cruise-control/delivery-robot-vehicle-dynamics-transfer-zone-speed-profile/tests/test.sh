#!/bin/bash
set -euo pipefail

pip3 install --break-system-packages \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5 \
    pyyaml==6.0.1

TEST_FILE="$(cd "$(dirname "$0")" && pwd)/test_outputs.py"
LOG_DIR="/logs/verifier"

mkdir -p "$LOG_DIR" 2>/dev/null || LOG_DIR="/tmp/harbor_logs/verifier"
mkdir -p "$LOG_DIR"

cd /root
if [ ! -f /root/zone_speed_profile.py ]; then
    echo "zone_speed_profile.py is missing"
    echo "0" > "$LOG_DIR/reward.txt"
    exit 1
fi

python3 /root/zone_speed_profile.py

set +e
pytest "$TEST_FILE" \
    --ctrf="$LOG_DIR/ctrf.json" \
    -v
status=$?
set -e

if [ "$status" -eq 0 ]; then
    echo "1" > "$LOG_DIR/reward.txt"
else
    echo "0" > "$LOG_DIR/reward.txt"
fi

exit "$status"
