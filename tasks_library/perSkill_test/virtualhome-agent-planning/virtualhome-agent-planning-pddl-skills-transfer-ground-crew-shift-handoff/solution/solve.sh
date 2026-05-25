#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import os
import yaml
import sys

sys.path.append("skills/pddl-skills")

class Skill:
    def __init__(self, name, expansion):
        self.name = name
        self.expansion = expansion

class SkillLibrary:
    def __init__(self, root):
        self.skills = {}
        self.load_skills(root)

    def load_skills(self, root):
        for path, _, files in os.walk(root):
            for filename in files:
                if not filename.endswith(".skill"):
                    continue
                with open(os.path.join(path, filename), "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                local_env = {}
                exec(data["script"], {}, local_env)
                self.skills[data["name"]] = Skill(data["name"], local_env["skill"])

    def expand(self, name, *args):
        return self.skills[name].expansion(*args)


def ensure_parent(path):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


with open("/app/problem.json", "r", encoding="utf-8") as f:
    tasks = json.load(f)

skills = SkillLibrary("skills")

for case in tasks:
    domain_file = case["domain"]
    problem_file = case["problem"]
    output_file = case["plan_output"]
    ensure_parent(output_file)

    problem_obj = skills.expand("load-problem", domain_file, problem_file)
    plan_obj = skills.expand("generate-plan", problem_obj)
    if plan_obj is None:
        raise RuntimeError(f"no plan found for {case['id']}")
    skills.expand("save-plan", problem_obj, plan_obj, output_file)
PY
