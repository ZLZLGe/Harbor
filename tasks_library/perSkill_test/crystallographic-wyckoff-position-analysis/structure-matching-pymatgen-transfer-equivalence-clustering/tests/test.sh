#!/bin/bash
set -euo pipefail

python3 /root/workspace/solution.py
python3 /tests/test_outputs.py
