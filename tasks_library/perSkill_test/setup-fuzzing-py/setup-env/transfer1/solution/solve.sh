#!/bin/bash
set -euo pipefail

cd /root/workspaces/releaseledger
uv sync
uv run -- python scripts/build_snapshot.py
