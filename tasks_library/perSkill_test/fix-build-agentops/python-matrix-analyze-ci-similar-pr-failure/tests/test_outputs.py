from pathlib import Path
import subprocess
import sys


WORKSPACE = Path("/workspace")
REPORT = WORKSPACE / "reports" / "pr-triage.md"
REPO = WORKSPACE / "repo"
SOURCE_FILE = REPO / "src" / "prstatus" / "summary.py"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_report_exists() -> None:
    require(REPORT.exists(), "reports/pr-triage.md 不存在")
    content = REPORT.read_text().strip()
    require(bool(content), "reports/pr-triage.md 为空")


def test_report_content() -> None:
    content = REPORT.read_text()
    content_lower = content.lower()
    required_snippets = [
        "PR #1421",
        "unit-tests (3.10)",
        "unit-tests (3.11)",
        "src/prstatus/summary.py",
        "format_python_job",
    ]
    for snippet in required_snippets:
        require(snippet in content, f"报告缺少关键信息: {snippet}")
    require(
        "test_format_python_job_preserves_dot" in content
        or "test_build_report_title_uses_matrix_label" in content,
        "报告没有指出受影响测试",
    )
    require(
        "python-311" in content
        or "python-310" in content
        or "missing dot" in content_lower
        or "少了小数点" in content
        or "移除了小数点" in content,
        "报告没有说明矩阵标签格式错误的具体表现",
    )


def test_fix_applied() -> None:
    content = SOURCE_FILE.read_text()
    require('python-{major}.{minor}' in content, "修复后的格式化逻辑未写入 summary.py")


def test_matrix_passes() -> None:
    result = subprocess.run(
        ["bash", str(REPO / "scripts" / "run_pr_matrix.sh")],
        cwd=str(REPO),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if result.returncode != 0:
        print(result.stdout)
    require(result.returncode == 0, "本地矩阵复现脚本仍然失败")


def main() -> None:
    tests = [
        test_report_exists,
        test_report_content,
        test_fix_applied,
        test_matrix_passes,
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
