#!/usr/bin/env bash
set -euo pipefail

WORKSPACE=/workspace
REPO="$WORKSPACE/repo"
REPORT_DIR="$WORKSPACE/reports"
REPORT="$REPORT_DIR/workflow-contract-findings.md"

mkdir -p "$REPORT_DIR"

cat > "$REPORT" <<'EOF'
# Workflow contract findings

## Failed jobs
- `analyze-service (api, 3.10)`
- `analyze-service (worker, 3.11)`

## Failure point
两个失败 job 都没有进入复用 workflow 的实际 steps，而是在 caller workflow `.github/workflows/service-analysis.yml` 调用 `.github/workflows/reusable-service-analysis.yml` 时直接被 GitHub Actions 校验拦下。

## Key evidence
- 两份日志都报出同一条错误：`Invalid input, python-version is not defined in the referenced workflow.`
- caller workflow 在 `with:` 里传入 `python-version`。
- reusable workflow 的 `workflow_call.inputs` 只声明了 `python_version`，没有声明 `python-version`。
- 下游 `publish-analysis-summary` 因为 `needs.analyze-service` 失败而被阻塞。

## Root cause
caller workflow 和 reusable workflow 的输入契约不一致。矩阵变量本身仍然使用 `matrix.python-version`，但调用复用 workflow 时把这个值映射到了不存在的 input 名 `python-version`，而被调用方实际声明的是 `python_version`。

## Fix plan
把 `.github/workflows/service-analysis.yml` 里的 `with.python-version` 改成 `with.python_version`，保持 caller 与 reusable workflow 的 input 名一致，然后重新运行 `scripts/run_reusable_contract_check.sh`。
EOF

python3 - <<'PY'
from pathlib import Path

workflow = Path("/workspace/repo/.github/workflows/service-analysis.yml")
text = workflow.read_text()
old = "      python-version: ${{ matrix.python-version }}\n"
new = "      python_version: ${{ matrix.python-version }}\n"
if old not in text:
    raise SystemExit("expected reusable workflow mismatch not found")
workflow.write_text(text.replace(old, new))
PY

bash "$REPO/scripts/run_reusable_contract_check.sh"
