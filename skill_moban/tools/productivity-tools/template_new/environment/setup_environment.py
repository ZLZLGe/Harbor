#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path


def resolve_src_root() -> Path:
    candidates = [
        Path("/opt/productivity-tools-task-env"),
        Path("/opt/productivity-tools-task-env/environment"),
    ]
    for candidate in candidates:
        if (candidate / "release_watch").exists() and (candidate / "workspace").exists():
            return candidate
    raise FileNotFoundError("Unable to locate bundled environment sources")


def ensure_dirs(paths: list[Path]) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def copy_tree(source: Path, destination: Path) -> None:
    shutil.copytree(source, destination, dirs_exist_ok=True)


def write_release_watch_baseline() -> None:
    baseline = Path("/opt/task-baselines/release-watch.sha256")
    release_root = Path("/app/release-watch")
    lines: list[str] = []
    for file_path in sorted(path for path in release_root.rglob("*") if path.is_file()):
        digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
        relpath = file_path.relative_to(release_root).as_posix()
        lines.append(f"{digest}  {relpath}")
    baseline.write_text("\n".join(lines) + "\n", encoding="utf-8")
    baseline.chmod(0o644)


def relax_permissions(root: Path) -> None:
    if not root.exists():
        return
    for dirpath, _, filenames in os.walk(root):
        Path(dirpath).chmod(0o777)
        for name in filenames:
            path = Path(dirpath) / name
            path.chmod(path.stat().st_mode | 0o666)


def install_codex_skill_sync() -> None:
    script = Path("/etc/profile.d/harbor-skill-sync.sh")
    script.write_text(
        """#!/bin/sh
SOURCE_ROOT=/root/.codex/skills
TARGET_HOME="${CODEX_HOME:-/tmp/codex-home}"
TARGET_ROOT="$TARGET_HOME/skills/.system"
if [ -d "$SOURCE_ROOT" ]; then
  mkdir -p "$TARGET_ROOT"
  : > "$TARGET_ROOT/.codex-system-skills.marker"
  for skill_dir in "$SOURCE_ROOT"/*; do
    [ -d "$skill_dir" ] || continue
    skill_name=$(basename "$skill_dir")
    mkdir -p "$TARGET_ROOT/$skill_name"
    cp -R "$skill_dir"/. "$TARGET_ROOT/$skill_name"/
  done
fi
""",
        encoding="utf-8",
    )
    script.chmod(0o755)

    hint = Path("/etc/codex-command-hint.sh")
    hint.write_text(
        """#!/bin/sh
if [ -f /root/.codex/skills/blogwatcher/SKILL.md ]; then
  export BLOGWATCHER_SKILL_HOME=/root/.codex/skills/blogwatcher
  echo "[blogwatcher] skill available at /root/.codex/skills/blogwatcher/SKILL.md" >&2
fi
""",
        encoding="utf-8",
    )
    hint.chmod(0o755)
    profile_hint = Path("/etc/profile.d/blogwatcher-skill.sh")
    profile_hint.write_text(hint.read_text(encoding="utf-8"), encoding="utf-8")
    profile_hint.chmod(0o755)


def main() -> int:
    src_root = resolve_src_root()
    skills_src = src_root / "skills"

    ensure_dirs(
        [
            Path("/app/release-watch"),
            Path("/app/workspace"),
            Path("/app/output"),
            Path("/app/skills"),
            Path("/environment/release-watch"),
            Path("/environment/workspace"),
            Path("/environment/skills"),
            Path("/tmp/codex-home/skills"),
            Path("/tmp/codex-home/skills/.system"),
            Path("/root/.codex/skills"),
            Path("/root/.claude/skills"),
            Path("/etc/claude-code/.claude/skills"),
            Path("/logs/agent/skills"),
            Path("/logs/verifier"),
            Path("/opt/task-baselines"),
        ]
    )

    copy_tree(src_root / "release_watch", Path("/app/release-watch"))
    copy_tree(src_root / "workspace", Path("/app/workspace"))
    copy_tree(src_root / "release_watch", Path("/environment/release-watch"))
    copy_tree(src_root / "workspace", Path("/environment/workspace"))

    if skills_src.exists():
        for destination in [
            Path("/app/skills"),
            Path("/environment/skills"),
            Path("/tmp/codex-home/skills"),
            Path("/tmp/codex-home/skills/.system"),
            Path("/root/.codex/skills"),
            Path("/root/.claude/skills"),
            Path("/etc/claude-code/.claude/skills"),
            Path("/logs/agent/skills"),
        ]:
            copy_tree(skills_src, destination)

    for path in [
        Path("/app/workspace/build_digest.py"),
        Path("/app/workspace/seed_watch_db.py"),
        Path("/environment/workspace/build_digest.py"),
        Path("/environment/workspace/seed_watch_db.py"),
    ]:
        path.chmod(0o755)

    for helper in [
        Path("/root/.codex/skills/blogwatcher/discover_local_feeds.py"),
        Path("/tmp/codex-home/skills/blogwatcher/discover_local_feeds.py"),
        Path("/tmp/codex-home/skills/.system/blogwatcher/discover_local_feeds.py"),
    ]:
        if helper.exists():
            helper.chmod(0o755)

    install_codex_skill_sync()
    write_release_watch_baseline()
    relax_permissions(Path("/app/workspace"))
    relax_permissions(Path("/app/output"))
    relax_permissions(Path("/logs"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
