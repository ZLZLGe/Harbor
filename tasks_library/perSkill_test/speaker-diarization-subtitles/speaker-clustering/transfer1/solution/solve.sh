#!/bin/bash
set -euo pipefail

mkdir -p /root/output
python3 /root/vendor/run_task.py /root/data/task_config.json
