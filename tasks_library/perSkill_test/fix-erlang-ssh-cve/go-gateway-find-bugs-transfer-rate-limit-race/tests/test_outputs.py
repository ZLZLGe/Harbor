from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


TASK_ROOT = Path(__file__).resolve().parents[1]


def resolve_report_path() -> Path:
    candidates = [
        Path("/app/workspace/reports/transfer-rate-limiter-findings.md"),
        TASK_ROOT / "reports" / "transfer-rate-limiter-findings.md",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[-1]


def resolve_repo_path() -> Path:
    candidates = [
        Path("/app/workspace/gateway-review"),
        TASK_ROOT / "environment" / "workspace" / "gateway-review",
    ]
    for path in candidates:
        if (path / ".git").exists():
            return path
    return candidates[-1]


def assert_contains(text: str, needle: str) -> None:
    assert needle in text, f"missing expected text: {needle!r}"


def main() -> None:
    report_path = resolve_report_path()
    repo_path = resolve_repo_path()

    assert report_path.exists(), f"report not found: {report_path}"
    assert (repo_path / ".git").exists(), f"repo not found: {repo_path}"

    content = report_path.read_text(encoding="utf-8")
    assert len(content.strip()) > 500, "report is unexpectedly short"

    assert_contains(content, "# Transfer - 审计 Go 租户限流器重构")
    assert_contains(content, "levi/tenant-limiter-refactor")
    assert_contains(content, "docs/review-brief.md")
    assert_contains(content, "internal/gateway/tenant_middleware.go")
    assert_contains(content, "internal/limiter/tenant_limiter.go")
    assert_contains(content, "internal/limiter/tenant_limiter_test.go")

    assert_contains(content, "High - 请求路径上的异步清理与 `tenants` map 无锁并发访问")
    assert_contains(content, "internal/gateway/tenant_middleware.go:31")
    assert_contains(content, "internal/gateway/tenant_middleware.go:34")
    assert_contains(content, "internal/limiter/tenant_limiter.go:58")
    assert_contains(content, "internal/limiter/tenant_limiter.go:92")
    assert_contains(content, "concurrent map read and map write")
    assert_contains(content, "TestSerialRequestsStayTenantScoped")
    assert_contains(content, "TestCleanupKeepsBusyTenant")
    assert_contains(content, "TestCleanupDropsIdleTenant")

    assert_contains(content, "High - 被限流请求会永久抬高 `inflight` 计数，清理失效并放大租户桶资源耗尽")
    assert_contains(content, "docs/review-brief.md:12")
    assert_contains(content, "internal/limiter/tenant_limiter.go:64")
    assert_contains(content, "internal/limiter/tenant_limiter.go:74")
    assert_contains(content, "internal/limiter/tenant_limiter.go:77")
    assert_contains(content, "internal/limiter/tenant_limiter.go:96")
    assert_contains(content, "tenant ID")
    assert_contains(content, "已检查但未发现新增问题")
    assert_contains(content, "核查清单")
    assert_contains(content, "无法完全验证的部分")

    diff_proc = subprocess.run(
        ["git", "-C", str(repo_path), "diff", "--name-only", "main...HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    changed_files = set(diff_proc.stdout.splitlines())
    expected = {
        "docs/review-brief.md",
        "internal/gateway/tenant_middleware.go",
        "internal/limiter/tenant_limiter.go",
        "internal/limiter/tenant_limiter_test.go",
    }
    assert expected == changed_files, changed_files

    branch_proc = subprocess.run(
        ["git", "-C", str(repo_path), "branch", "--show-current"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert branch_proc.stdout.strip() == "levi/tenant-limiter-refactor", branch_proc.stdout

    if shutil.which("go"):
        go_test_proc = subprocess.run(
            ["go", "test", "./..."],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
        assert go_test_proc.returncode == 0, (
            "go test failed\n"
            f"stdout:\n{go_test_proc.stdout}\n"
            f"stderr:\n{go_test_proc.stderr}\n"
        )


if __name__ == "__main__":
    main()
