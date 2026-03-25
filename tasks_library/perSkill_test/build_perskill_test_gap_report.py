#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


DEFAULT_SOURCE_ROOT = Path("/home/levi/Harbor/tasks_library/skillsbench/tasks")
DEFAULT_TARGET_ROOT = Path("/home/levi/Harbor/tasks_library/perSkill_test")
DEFAULT_OUTPUT = DEFAULT_TARGET_ROOT / "perSkill_test_gap_report.md"
EXPECTED_TASKS_PER_SKILL = 4


@dataclass(frozen=True)
class MissingTaskRow:
    source_task_id: str
    expected_skills: list[str]


@dataclass(frozen=True)
class SkillGapRow:
    source_task_id: str
    skill_dir: str
    actual_task_count: int
    missing_task_count: int
    existing_task_ids: list[str]


@dataclass(frozen=True)
class IgnoredDirRow:
    source_task_id: str
    child_dir: str
    reason: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a gap report comparing skillsbench source tasks against perSkill_test coverage.",
    )
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--target-root", type=Path, default=DEFAULT_TARGET_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def list_dir_names(root: Path) -> list[str]:
    if not root.exists():
        return []
    return sorted(path.name for path in root.iterdir() if path.is_dir())


def read_source_skills(task_dir: Path) -> list[str]:
    skills_dir = task_dir / "environment" / "skills"
    if not skills_dir.is_dir():
        return []
    return sorted(path.name for path in skills_dir.iterdir() if path.is_dir())


def markdown_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("|", "\\|").replace("\n", "<br>")


def format_list(values: Iterable[str]) -> str:
    items = [item for item in values if item]
    return ", ".join(items) if items else "-"


def render_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    if not rows:
        return ["_无_"]

    output = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        output.append("| " + " | ".join(markdown_escape(cell) for cell in row) + " |")
    return output


def classify_child_dir(child_dir: Path) -> tuple[bool, str | None, str | None]:
    task_toml = child_dir / "task.toml"
    skills_dir = child_dir / "environment" / "skills"

    if not task_toml.is_file():
        return False, None, "missing task.toml"
    if not skills_dir.is_dir():
        return False, None, "missing environment/skills"

    skill_names = sorted(path.name for path in skills_dir.iterdir() if path.is_dir())
    if len(skill_names) == 0:
        return False, None, "zero skills"
    if len(skill_names) > 1:
        return False, None, "multiple skills"

    return True, skill_names[0], None


def build_report(source_root: Path, target_root: Path) -> str:
    source_task_dirs = sorted(path for path in source_root.iterdir() if path.is_dir())
    target_task_dirs = {
        path.name: path
        for path in target_root.iterdir()
        if path.is_dir() and path.name != "jobs"
    }

    missing_tasks: list[MissingTaskRow] = []
    skill_gaps: list[SkillGapRow] = []
    ignored_dirs: list[IgnoredDirRow] = []

    for source_task_dir in source_task_dirs:
        source_task_id = source_task_dir.name
        expected_skills = read_source_skills(source_task_dir)
        target_task_dir = target_task_dirs.get(source_task_id)

        if target_task_dir is None:
            missing_tasks.append(
                MissingTaskRow(
                    source_task_id=source_task_id,
                    expected_skills=expected_skills,
                )
            )
            continue

        skill_to_task_ids: dict[str, list[str]] = defaultdict(list)

        for child_dir in sorted(path for path in target_task_dir.iterdir() if path.is_dir()):
            is_valid, skill_name, reason = classify_child_dir(child_dir)
            if not is_valid:
                ignored_dirs.append(
                    IgnoredDirRow(
                        source_task_id=source_task_id,
                        child_dir=child_dir.name,
                        reason=reason or "missing task.toml",
                    )
                )
                continue

            assert skill_name is not None
            skill_to_task_ids[skill_name].append(child_dir.name)

        for skill_name in expected_skills:
            existing_task_ids = sorted(skill_to_task_ids.get(skill_name, []))
            actual_count = len(existing_task_ids)
            if actual_count < EXPECTED_TASKS_PER_SKILL:
                skill_gaps.append(
                    SkillGapRow(
                        source_task_id=source_task_id,
                        skill_dir=skill_name,
                        actual_task_count=actual_count,
                        missing_task_count=EXPECTED_TASKS_PER_SKILL - actual_count,
                        existing_task_ids=existing_task_ids,
                    )
                )

    source_task_total = len(source_task_dirs)
    present_source_task_count = source_task_total - len(missing_tasks)
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")

    lines: list[str] = [
        "# perSkill_test 缺口盘点报告",
        "",
        "## 快照信息",
        "",
        f"- 生成时间: `{generated_at}`",
        f"- source root: `{source_root}`",
        f"- target root: `{target_root}`",
        f"- 统计口径: 每个 shipped skill 目标 task 数固定为 `{EXPECTED_TASKS_PER_SKILL}`；`>= {EXPECTED_TASKS_PER_SKILL}` 视为已跑满，`< {EXPECTED_TASKS_PER_SKILL}` 视为缺口。",
        "",
        "## 总览",
        "",
        f"- source task 总数: `{source_task_total}`",
        f"- perSkill_test 中已出现的 source task 数: `{present_source_task_count}`",
        f"- 顶层完全未出现的 source task 数: `{len(missing_tasks)}`",
        f"- 未跑满 4 个 task 的 skill 数: `{len(skill_gaps)}`",
        f"- 被忽略的异常目录数: `{len(ignored_dirs)}`",
        "",
        "## 完全未出现的 source task",
        "",
    ]

    missing_task_rows = [
        [
            row.source_task_id,
            format_list(row.expected_skills),
            str(len(row.expected_skills) * EXPECTED_TASKS_PER_SKILL),
        ]
        for row in sorted(missing_tasks, key=lambda row: row.source_task_id)
    ]
    lines.extend(
        render_table(
            ["source_task_id", "expected_skills", "expected_task_count"],
            missing_task_rows,
        )
    )

    lines.extend([
        "",
        "## 未跑满 4 个 task 的 skill",
        "",
    ])
    skill_gap_rows = [
        [
            row.source_task_id,
            row.skill_dir,
            str(row.actual_task_count),
            str(row.missing_task_count),
            format_list(row.existing_task_ids),
        ]
        for row in sorted(
            skill_gaps,
            key=lambda row: (row.actual_task_count, row.source_task_id, row.skill_dir),
        )
    ]
    lines.extend(
        render_table(
            [
                "source_task_id",
                "skill_dir",
                "actual_task_count",
                "missing_task_count",
                "existing_task_ids",
            ],
            skill_gap_rows,
        )
    )

    lines.extend([
        "",
        "## 忽略的异常目录",
        "",
        f"异常目录数量: `{len(ignored_dirs)}`",
        "",
    ])
    ignored_dir_rows = [
        [row.source_task_id, row.child_dir, row.reason]
        for row in sorted(ignored_dirs, key=lambda row: (row.source_task_id, row.child_dir, row.reason))
    ]
    lines.extend(
        render_table(
            ["source_task_id", "child_dir", "reason"],
            ignored_dir_rows,
        )
    )

    lines.extend([
        "",
        "## 统计说明",
        "",
        "- 本报告按 source task 的 shipped skills 统计。",
        f"- 每个 shipped skill 的目标数量固定按 `{EXPECTED_TASKS_PER_SKILL}` 计算。",
        f"- `actual_task_count > {EXPECTED_TASKS_PER_SKILL}` 不算缺口，不会在本报告中单列问题。",
        "- `perSkill_test` 顶层的 `jobs` 目录已忽略。",
        "- 异常目录不会计入任何 skill 的有效 task 数。",
        "",
    ])

    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    source_root = args.source_root.resolve()
    target_root = args.target_root.resolve()
    output_path = args.output.resolve()

    report = build_report(source_root, target_root)
    output_path.write_text(report + "\n", encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()
