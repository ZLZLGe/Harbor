import json
from pathlib import Path
import subprocess
import sys


WORKSPACE = Path("/workspace")
REPORT = WORKSPACE / "reports" / "docs-build-investigation.md"
REPO = WORKSPACE / "repo"
PACKAGE_LOCK = REPO / "docs" / "package-lock.json"
OUTPUT_HTML = REPO / "docs" / "dist" / "index.html"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_report_exists() -> None:
    require(REPORT.exists(), "reports/docs-build-investigation.md 不存在")
    require(REPORT.read_text().strip(), "reports/docs-build-investigation.md 为空")


def test_report_content() -> None:
    content = REPORT.read_text()
    required_snippets = [
        "docs-build",
        "docs-preview-smoke",
        "npm ci",
        "docs/package-lock.json",
        "docs/package.json",
        "@harbor/theme-utils",
        ".github/workflows/docs-site.yml",
    ]
    for snippet in required_snippets:
        require(snippet in content, f"报告缺少关键信息: {snippet}")
    require(
        "lock file" in content.lower() or "锁文件" in content,
        "报告没有明确说明锁文件漂移问题",
    )


def test_lockfile_updated() -> None:
    lock = json.loads(PACKAGE_LOCK.read_text())
    root_deps = lock["packages"][""]["dependencies"]
    require(
        root_deps.get("@harbor/theme-utils") == "file:../packages/theme-utils",
        "package-lock.json 没有同步记录 @harbor/theme-utils",
    )
    require(
        "node_modules/@harbor/theme-utils" in lock["packages"],
        "package-lock.json 缺少 theme-utils 的安装条目",
    )


def test_docs_ci_passes() -> None:
    result = subprocess.run(
        ["bash", str(REPO / "scripts" / "run_docs_ci.sh")],
        cwd=str(REPO),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if result.returncode != 0:
        print(result.stdout)
    require(result.returncode == 0, "文档 CI 复现脚本仍然失败")


def test_output_html() -> None:
    require(OUTPUT_HTML.exists(), "docs/dist/index.html 未生成")
    content = OUTPUT_HTML.read_text()
    require("<title>Harbor Docs</title>" in content, "构建产物缺少页面标题")
    require("Deployment Checklist" in content, "构建产物缺少文档内容")


def main() -> None:
    tests = [
        test_report_exists,
        test_report_content,
        test_lockfile_updated,
        test_docs_ci_passes,
        test_output_html,
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
