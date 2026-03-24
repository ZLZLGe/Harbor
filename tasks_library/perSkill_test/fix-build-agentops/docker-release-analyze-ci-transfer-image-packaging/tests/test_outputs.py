import tarfile
from pathlib import Path
import subprocess
import sys


WORKSPACE = Path("/workspace")
REPORT = WORKSPACE / "reports" / "release-pipeline-report.md"
REPO = WORKSPACE / "repo"
DOCKERFILE = REPO / "Dockerfile"
BUNDLE = REPO / "dist" / "harbor-release-bundle.tgz"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_report_exists() -> None:
    require(REPORT.exists(), "reports/release-pipeline-report.md 不存在")
    require(REPORT.read_text().strip(), "reports/release-pipeline-report.md 为空")


def test_report_content() -> None:
    content = REPORT.read_text()
    required_snippets = [
        "release-image",
        "package-release-bundle",
        "docker build",
        "COPY packaging/assets/ /opt/harbor/release/",
        "packaging/release/",
        "/workspace/repo/Dockerfile",
        ".github/workflows/release-image.yml",
    ]
    for snippet in required_snippets:
        require(snippet in content, f"报告缺少关键信息: {snippet}")


def test_dockerfile_fixed() -> None:
    content = DOCKERFILE.read_text()
    require(
        "COPY packaging/release/ /opt/harbor/release/" in content,
        "Dockerfile 没有改成正确的发布资源路径",
    )


def test_release_ci_passes() -> None:
    result = subprocess.run(
        ["bash", str(REPO / "scripts" / "run_release_ci.sh")],
        cwd=str(REPO),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if result.returncode != 0:
        print(result.stdout)
    require(result.returncode == 0, "本地发布复现脚本仍然失败")


def test_bundle_contents() -> None:
    require(BUNDLE.exists(), "发布 bundle 没有生成")
    with tarfile.open(BUNDLE, "r:gz") as archive:
        names = set(archive.getnames())
    for name in {
        "release/release-manifest.json",
        "release/entrypoint.sh",
        "app/main.py",
        "app/version.txt",
    }:
        require(name in names, f"bundle 缺少文件: {name}")


def main() -> None:
    tests = [
        test_report_exists,
        test_report_content,
        test_dockerfile_fixed,
        test_release_ci_passes,
        test_bundle_contents,
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
