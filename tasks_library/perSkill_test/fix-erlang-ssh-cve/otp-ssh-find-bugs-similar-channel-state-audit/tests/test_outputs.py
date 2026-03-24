from __future__ import annotations

import os
import subprocess
from pathlib import Path


TASK_ROOT = Path(__file__).resolve().parents[1]


def resolve_report_path() -> Path:
    candidates = [
        Path("/app/workspace/reports/similar-ssh-channel-findings.md"),
        TASK_ROOT / "reports" / "similar-ssh-channel-findings.md",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[-1]


def resolve_repo_path() -> Path:
    candidates = [
        Path("/app/workspace/otp-ssh-review"),
        TASK_ROOT / "environment" / "workspace" / "otp-ssh-review",
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
    assert len(content.strip()) > 400, "report is unexpectedly short"

    assert_contains(content, "# Similar - 审计 Erlang SSH Channel 状态机加固补丁")
    assert_contains(content, "levi/ssh-channel-hardening")
    assert_contains(content, "docs/review-brief.md")
    assert_contains(content, "lib/ssh/src/ssh_connection.erl")
    assert_contains(content, "lib/ssh/src/ssh_server_channel.erl")
    assert_contains(content, "lib/ssh/test/ssh_channel_state_SUITE.erl")

    assert_contains(content, "High - `subsystem` 仍可沿未认证路径进入子系统启动逻辑")
    assert_contains(content, "lib/ssh/src/ssh_connection.erl:31")
    assert_contains(content, "lib/ssh/src/ssh_server_channel.erl:53")
    assert_contains(content, "preauth_exec_disconnects")
    assert_contains(content, "preauth_subsystem_disconnects")

    assert_contains(content, "Medium - 认证后的普通 `shell` 会话被错误地要求必须先申请 PTY")
    assert_contains(content, "authenticated_shell_without_pty_works")
    assert_contains(content, "authenticated_shell_after_pty_works")
    assert_contains(content, "reply_failure")

    assert_contains(content, "已检查但未发现新增问题")
    assert_contains(content, "核查清单")
    assert_contains(content, "无法完全验证的部分")

    proc = subprocess.run(
        ["git", "-C", str(repo_path), "branch", "--show-current"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert proc.stdout.strip() == "levi/ssh-channel-hardening", proc.stdout


if __name__ == "__main__":
    main()
