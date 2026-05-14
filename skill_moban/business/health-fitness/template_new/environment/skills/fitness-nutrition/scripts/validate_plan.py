from __future__ import annotations

import csv
import json
from pathlib import Path

from planner_core import OUTPUT_ROOT, load_inputs, validate_outputs


def load_workout() -> dict:
    return json.loads((OUTPUT_ROOT / "workout_plan.json").read_text(encoding="utf-8"))


def load_summary() -> dict:
    return json.loads((OUTPUT_ROOT / "plan_summary.json").read_text(encoding="utf-8"))


def load_handoff() -> str:
    return (OUTPUT_ROOT / "coach_handoff.md").read_text(encoding="utf-8")


def load_meal_rows() -> list[dict]:
    with (OUTPUT_ROOT / "meal_plan.csv").open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main() -> None:
    inputs = load_inputs()
    validate_outputs(load_workout(), load_meal_rows(), load_summary(), load_handoff(), inputs)
    print("ok")


if __name__ == "__main__":
    main()
