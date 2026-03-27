import csv
import json
import os
import re
from pathlib import Path

import yaml


class Skill:
    def __init__(self, name, func):
        self.name = name
        self.func = func


class SkillLibrary:
    def __init__(self, skill_root):
        self.skills = {}
        self._load(skill_root)

    def _load(self, skill_root):
        for path in Path(skill_root).rglob("*.skill"):
            with open(path, "r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle)
            local_env = {}
            exec(data["script"], {}, local_env)
            self.skills[data["name"]] = Skill(data["name"], local_env["skill"])

    def expand(self, skill_name, *args):
        return self.skills[skill_name].func(*args)


def read_plan_lines(path):
    with open(path, "r", encoding="utf-8") as handle:
        return [line.strip() for line in handle if line.strip() and not line.lstrip().startswith(";")]


def action_name(action_line):
    match = re.match(r"^\(?([A-Za-z0-9_-]+)", action_line.strip())
    if not match:
        raise ValueError(f"Cannot extract action name from line: {action_line}")
    return match.group(1)


def count_actions(lines, target_name):
    return sum(1 for line in lines if action_name(line) == target_name)


def solve_cases(config_path, skill_root):
    with open(config_path, "r", encoding="utf-8") as handle:
        config = json.load(handle)

    skills = SkillLibrary(skill_root)
    records = []
    for case in sorted(config["cases"], key=lambda item: item["case_id"]):
        problem = skills.expand("load-problem", case["domain"], case["problem"])
        plan = skills.expand("generate-plan", problem)
        if plan is None:
            raise RuntimeError(f"No plan generated for {case['case_id']}")
        if not skills.expand("validate", problem, plan):
            raise RuntimeError(f"Plan failed validation for {case['case_id']}")

        output_path = Path(case["plan_output"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        skills.expand("save-plan", problem, plan, str(output_path))

        lines = read_plan_lines(output_path)
        if not lines:
            raise RuntimeError(f"Empty plan written for {case['case_id']}")

        records.append(
            {
                "case_id": case["case_id"],
                "plan_file": str(output_path),
                "steps": len(lines),
                "action_count": len(lines),
                "first_action": lines[0],
                "last_action": lines[-1],
                "terminal_action": lines[-1],
                "pick_actions": count_actions(lines, "pick"),
                "drop_actions": count_actions(lines, "drop"),
                "capture_actions": count_actions(lines, "capture-photo"),
            }
        )

    write_summary(config, records)


def write_summary(config, records):
    fmt = config["summary_format"]
    output_path = Path(config["summary_output"])
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "json_manifest":
        payload = {
            "scenario": config["scenario"],
            "cases": [
                {
                    "case_id": record["case_id"],
                    "plan_file": record["plan_file"],
                    "action_count": record["action_count"],
                    "first_action": record["first_action"],
                    "last_action": record["last_action"],
                }
                for record in records
            ],
        }
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
        return

    if fmt == "csv_dispatch":
        with open(output_path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["case_id", "plan_file", "steps", "pick_actions", "drop_actions"],
            )
            writer.writeheader()
            for record in records:
                writer.writerow(
                    {
                        "case_id": record["case_id"],
                        "plan_file": record["plan_file"],
                        "steps": record["steps"],
                        "pick_actions": record["pick_actions"],
                        "drop_actions": record["drop_actions"],
                    }
                )
        return

    if fmt == "markdown_runbook":
        lines = [
            "# Lab Runbook",
            "",
            "| case_id | plan_file | steps | terminal_action |",
            "| --- | --- | ---: | --- |",
        ]
        for record in records:
            lines.append(
                f"| {record['case_id']} | {record['plan_file']} | {record['steps']} | {record['terminal_action']} |"
            )
        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        return

    if fmt == "text_digest":
        lines = []
        for record in records:
            lines.extend(
                [
                    f"case_id={record['case_id']}",
                    f"plan_file={record['plan_file']}",
                    f"steps={record['steps']}",
                    f"capture_actions={record['capture_actions']}",
                    f"final_action={record['terminal_action']}",
                    "",
                ]
            )
        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines).rstrip() + "\n")
        return

    raise ValueError(f"Unsupported summary format: {fmt}")


if __name__ == "__main__":
    config_path = os.environ.get("PLANNING_BATCH_CONFIG", "/root/airport_batch.json")
    solve_cases(config_path, "/root/skills/pddl-skills")
