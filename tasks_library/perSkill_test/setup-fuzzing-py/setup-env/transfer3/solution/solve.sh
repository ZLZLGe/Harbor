#!/bin/bash
set -euo pipefail

cd /root/workspaces/templategen
uv sync
uv run -- python -m templategen.cli config.json /root/transfer3_rendered.md

cat > /root/transfer3_command_log.md <<'EOF'
- workspace: /root/workspaces/templategen
- command: uv sync
- command: uv run -- python -m templategen.cli config.json /root/transfer3_rendered.md
EOF
