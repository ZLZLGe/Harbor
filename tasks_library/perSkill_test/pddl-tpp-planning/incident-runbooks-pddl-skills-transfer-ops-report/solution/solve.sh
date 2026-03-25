#!/bin/bash

set -euo pipefail

mkdir -p results/plans

python3 <<'PY'
import json
import os
import yaml


class Skill:
    def __init__(self, name, fn):
        self.name = name
        self.fn = fn


class SkillLibrary:
    def __init__(self, root):
        self.skills = {}
        self._load(root)

    def _load(self, root):
        for current_root, _, files in os.walk(root):
            for filename in files:
                if not filename.endswith(".skill"):
                    continue
                path = os.path.join(current_root, filename)
                data = yaml.safe_load(open(path, "r", encoding="utf-8"))
                scope = {}
                exec(data["script"], {}, scope)
                self.skills[data["name"]] = Skill(data["name"], scope["skill"])

    def call(self, name, *args):
        return self.skills[name].fn(*args)


def main():
    manifest_path = "/app/runbooks/incidents.json"
    with open(manifest_path, "r", encoding="utf-8") as handle:
        manifest = json.load(handle)

    skills = SkillLibrary("/app/skills/pddl-skills")
    domain_path = os.path.join("/app", manifest["domain"])
    report = {"incidents": []}

    for incident in manifest["incidents"]:
        problem_path = os.path.join("/app", incident["problem"])
        plan_path = os.path.join("/app", incident["plan_output"])
        problem = skills.call("load-problem", domain_path, problem_path)
        plan = skills.call("generate-plan", problem)

        if plan is None:
            report["incidents"].append(
                {
                    "incident_id": incident["incident_id"],
                    "status": "unsolved",
                    "actions": [],
                    "action_count": 0,
                    "plan_file": None,
                }
            )
            continue

        os.makedirs(os.path.dirname(plan_path), exist_ok=True)
        with open(plan_path, "w", encoding="utf-8") as handle:
            for action in plan.actions:
                handle.write(f"{action}\n")

        report["incidents"].append(
            {
                "incident_id": incident["incident_id"],
                "status": "solved",
                "actions": [str(action) for action in plan.actions],
                "action_count": len(plan.actions),
                "plan_file": incident["plan_output"],
            }
        )

    os.makedirs("/app/results", exist_ok=True)
    with open("/app/results/incident-runbooks.json", "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    main()
PY
