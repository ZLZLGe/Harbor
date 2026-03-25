#!/bin/bash
set -euo pipefail

cd /root/workspaces/deltaqueue
uv venv
uv pip install -r requirements.txt
.venv/bin/python scripts/normalize_jobs.py
