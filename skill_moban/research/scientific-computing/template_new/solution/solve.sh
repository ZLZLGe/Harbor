#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "${SCRIPT_DIR}/fixed_run_analysis.py" /root/workspace/run_analysis.py
chmod +x /root/workspace/run_analysis.py
python /root/workspace/run_analysis.py --data /root/data --output /root/output
