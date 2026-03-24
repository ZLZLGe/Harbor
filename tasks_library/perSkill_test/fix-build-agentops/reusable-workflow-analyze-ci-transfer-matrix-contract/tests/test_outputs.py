from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


WORKSPACE = Path("/workspace")
REPORT = WORKSPACE / "reports" / "workflow-contract-findings.md"
REPO = WORKSPACE / "repo"
CALLER_WORKFLOW = REPO / ".github" / "workflows" / "service-analysis.yml"
REUSABLE_WORKFLOW = REPO / ".github" / "workflows" / "reusable-service-analysis.yml"
CHECK_SCRIPT = REPO / "scripts" / "run_reusable_contract_check.sh"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def extract_with_keys(lines: list[str]) -> list[str]:
    in_with = False
    keys: list[str] = []
    for line in lines:
        if re.match(r"^\s{4}with:\s*$", line):
            in_with = True
            continue
        if not in_with:
            continue
        key_match = re.match(r"^\s{6}([A-Za-z0-9_-]+):\s*", line)
        if key_match:
            keys.append(key_match.group(1))
            continue
        if line.strip() == "":
            continue
        if re.match(r"^\s{2}[A-Za-z0-9_-]+:\s*$", line) or re.match(r"^\s{4}[A-Za-z0-9_-]+:\s*$", line):
            break
    return keys


def extract_reusable_inputs(lines: list[str]) -> list[str]:
    in_workflow_call = False
    in_inputs = False
    inputs: list[str] = []
    for line in lines:
        if re.match(r"^\s{2}workflow_call:\s*$", line):
            in_workflow_call = True
            continue
        if not in_workflow_call:
            continue
        if re.match(r"^\s{4}inputs:\s*$", line):
            in_inputs = True
            continue
        if in_inputs:
            key_match = re.match(r"^\s{6}([A-Za-z0-9_-]+):\s*$", line)
            if key_match:
                inputs.append(key_match.group(1))
                continue
            if line.strip() == "":
                continue
            if re.match(r"^\s{2}[A-Za-z0-9_-]+:\s*$", line):
                break
    return inputs


def test_report_exists() -> None:
    require(REPORT.exists(), "reports/workflow-contract-findings.md 不存在")
    require(REPORT.read_text().strip(), "reports/workflow-contract-findings.md 为空")


def test_report_content() -> None:
    content = REPORT.read_text()
    required_snippets = [
        "analyze-service (api, 3.10)",
        "analyze-service (worker, 3.11)",
        "publish-analysis-summary",
        "python-version",
        "python_version",
        ".github/workflows/service-analysis.yml",
        ".github/workflows/reusable-service-analysis.yml",
    ]
    for snippet in required_snippets:
        require(snippet in content, f"报告缺少关键信息: {snippet}")
    require(
        "Invalid input" in content or "契约" in content or "contract" in content.lower(),
        "报告没有明确说明 reusable workflow 输入契约错误",
    )


def test_workflow_contract_fixed() -> None:
    caller_keys = extract_with_keys(CALLER_WORKFLOW.read_text().splitlines())
    reusable_inputs = extract_reusable_inputs(REUSABLE_WORKFLOW.read_text().splitlines())

    require("service_name" in caller_keys, "caller workflow 缺少 service_name")
    require("artifact_prefix" in caller_keys, "caller workflow 缺少 artifact_prefix")
    require("service_name" in reusable_inputs, "reusable workflow 缺少 service_name input")
    require("artifact_prefix" in reusable_inputs, "reusable workflow 缺少 artifact_prefix input")

    missing = [key for key in caller_keys if key not in reusable_inputs]
    require(not missing, f"caller workflow 仍然在传递未声明的 inputs: {missing}")


def test_contract_check_passes() -> None:
    result = subprocess.run(
        ["bash", str(CHECK_SCRIPT)],
        cwd=str(REPO),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if result.returncode != 0:
        print(result.stdout)
    require(result.returncode == 0, "本地 reusable workflow 契约检查仍然失败")
    require("PASS analyze-service (api, 3.10)" in result.stdout, "api matrix job 没有通过契约检查")
    require("PASS analyze-service (worker, 3.11)" in result.stdout, "worker matrix job 没有通过契约检查")
    require("PASS publish-analysis-summary" in result.stdout, "下游汇总 job 没有恢复")


def main() -> None:
    tests = [
        test_report_exists,
        test_report_content,
        test_workflow_contract_fixed,
        test_contract_check_passes,
    ]
    for test in tests:
        test()
    print("all checks passed")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"TEST FAILURE: {exc}", file=sys.stderr)
        sys.exit(1)
