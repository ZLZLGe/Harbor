#!/bin/bash
set -euo pipefail

REPO_ROOT=/workspace/scoreboard-service

mkdir -p "$REPO_ROOT/ci-notes"
cat <<'EOF' > "$REPO_ROOT/ci-notes/plan.txt"
当前 workflow 仍然依赖不存在的 requirements.txt，所以安装步骤会失败。
修复方式是保留 setup-python，改为使用仓库已有的 lockfile 同步环境，
再通过同一环境执行 unittest。
EOF

cat <<'EOF' > "$REPO_ROOT/.github/workflows/python-ci.yml"
name: Python CI

on:
  push:
    branches:
      - main
  pull_request:

jobs:
  tests:
    runs-on: ubuntu-latest
    steps:
      - name: Check out repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install project environment
        run: uv sync --locked

      - name: Run tests
        run: uv run python -m unittest discover -s tests -q
EOF

cd "$REPO_ROOT"
python scripts/local_ci_check.py
