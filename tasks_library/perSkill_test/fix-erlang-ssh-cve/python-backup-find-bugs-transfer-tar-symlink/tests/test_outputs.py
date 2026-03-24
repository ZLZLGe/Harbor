from __future__ import annotations

import subprocess
from pathlib import Path


TASK_ROOT = Path(__file__).resolve().parents[1]


def resolve_report_path() -> Path:
    candidates = [
        Path("/app/workspace/reports/transfer-backup-archive-findings.md"),
        TASK_ROOT / "reports" / "transfer-backup-archive-findings.md",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[-1]


def resolve_repo_path() -> Path:
    candidates = [
        Path("/app/workspace/backup-restore-review"),
        TASK_ROOT / "environment" / "workspace" / "backup-restore-review",
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

    assert_contains(content, "# Transfer - 审计 Python 备份恢复归档处理改动")
    assert_contains(content, "levi/tar-restore-hardening")
    assert_contains(content, "docs/review-brief.md")
    assert_contains(content, "src/backup_restore/archive_restore.py")
    assert_contains(content, "src/backup_restore/restore_job.py")
    assert_contains(content, "tests/test_restore.py")

    assert_contains(content, "High - `TarInfo.linkname` 完全未校验")
    assert_contains(content, "src/backup_restore/archive_restore.py:9")
    assert_contains(content, "src/backup_restore/archive_restore.py:12")
    assert_contains(content, "src/backup_restore/archive_restore.py:30")
    assert_contains(content, "test_rejects_absolute_member")
    assert_contains(content, "test_rejects_dotdot_member")

    assert_contains(content, "High - 清单回放阶段会跟随已解包的符号链接写入标记文件")
    assert_contains(content, "src/backup_restore/restore_job.py:15")
    assert_contains(content, "src/backup_restore/restore_job.py:17")
    assert_contains(content, "src/backup_restore/restore_job.py:18")
    assert_contains(content, "src/backup_restore/restore_job.py:21")
    assert_contains(content, "test_manifest_marker_written")

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
        "src/backup_restore/archive_restore.py",
        "src/backup_restore/restore_job.py",
        "tests/test_restore.py",
    }
    assert expected.issubset(changed_files), changed_files

    branch_proc = subprocess.run(
        ["git", "-C", str(repo_path), "branch", "--show-current"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert branch_proc.stdout.strip() == "levi/tar-restore-hardening", branch_proc.stdout


if __name__ == "__main__":
    main()
