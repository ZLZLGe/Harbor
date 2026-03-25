#!/bin/bash
set -euo pipefail

for repo in bytescout cfgweave pathaudit; do
    cd "/root/workspaces/${repo}"
    if [ -f pyproject.toml ]; then
        uv sync
        case "$repo" in
            cfgweave)
                uv run -- python scripts/render_status.py
                ;;
        esac
    elif [ -f requirements.txt ]; then
        uv venv
        uv pip install -r requirements.txt
        case "$repo" in
            bytescout)
                .venv/bin/python scripts/emit_status.py
                ;;
            pathaudit)
                .venv/bin/python scripts/check_paths.py
                ;;
        esac
    else
        echo "missing project metadata for $repo" >&2
        exit 1
    fi
done

cat > /root/similar_env_summary.txt <<'EOF'
bytescout: requirements workflow complete
cfgweave: pyproject workflow complete
pathaudit: requirements workflow complete
EOF
