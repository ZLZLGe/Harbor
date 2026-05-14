#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

rm -rf /root/app
mkdir -p /root/app /root/output
cp -R "$SCRIPT_DIR/fixed/app/." /root/app/

python3 /root/app/main.py --data-root /root/data --output-root /root/output
