from __future__ import annotations

import json

from planner_core import build_workout_plan, load_inputs


def main() -> None:
    inputs = load_inputs()
    workout, summary = build_workout_plan(inputs)
    payload = {"workout_plan": workout, "summary": summary}
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
