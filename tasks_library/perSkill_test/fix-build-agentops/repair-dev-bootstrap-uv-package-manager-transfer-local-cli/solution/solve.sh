#!/bin/bash
set -euo pipefail

REPO_ROOT=/workspace/dev-bootstrap-station
cd "$REPO_ROOT"

mkdir -p notes
cat > notes/bootstrap-plan.txt <<'EOF'
当前引导脚本有两个核心问题：
1. 它硬编码了 `python3.10`，和仓库约定的解释器版本不一致，开发环境里很容易直接失败。
2. 它依赖手动激活虚拟环境、`pip install -e .` 和裸入口命令，环境与 CLI 运行方式不统一。

修复方式：
- 从 `.python-version` 读取仓库约定的 Python 版本；
- 用同一个版本创建 `.venv`；
- 通过同一套环境运行 `python -m devbootstrap.cli`，生成 `var/bootstrap_report.txt`。
EOF

cat > scripts/bootstrap_env.sh <<'EOF'
#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PYTHON_VERSION="$(tr -d '\n' < "$REPO_ROOT/.python-version")"

uv venv .venv --python "$PYTHON_VERSION"
uv run --python "$PYTHON_VERSION" python -m devbootstrap.cli \
  --seed data/bootstrap_seed.json \
  --output var/bootstrap_report.txt
EOF

python tools/check_bootstrap.py
