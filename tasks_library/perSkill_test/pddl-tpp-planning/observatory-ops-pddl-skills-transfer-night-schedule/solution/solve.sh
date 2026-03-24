#!/bin/bash

set -euo pipefail

python3 <<'PY'
import json
import os
import yaml


class SkillLibrary:
    def __init__(self, root):
        self.skills = {}
        self._load(root)

    def _load(self, root):
        for current_root, _, files in os.walk(root):
            for filename in files:
                if not filename.endswith(".skill"):
                    continue
                skill_path = os.path.join(current_root, filename)
                with open(skill_path, "r", encoding="utf-8") as handle:
                    data = yaml.safe_load(handle)
                scope = {}
                exec(data["script"], {}, scope)
                self.skills[data["name"]] = scope["skill"]

    def run(self, name, *args):
        return self.skills[name](*args)


skills = SkillLibrary("skills")

with open("night_windows.json", "r", encoding="utf-8") as handle:
    schedules = json.load(handle)

for item in schedules:
    output_path = item["plan_output"]
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    problem = skills.run("load-problem", item["domain"], item["problem"])
    plan = skills.run("generate-plan", problem)
    if plan is None:
        raise RuntimeError(f"No plan found for {item['id']}")
    if not skills.run("validate", problem, plan):
        raise RuntimeError(f"Invalid plan generated for {item['id']}")
    skills.run("save-plan", plan, output_path)
PY
