from __future__ import annotations

import json

from planner_core import exercise_candidates, load_inputs


def main() -> None:
    inputs = load_inputs()
    result = {}
    for day_template in inputs["rules"]["workout_rules"]["day_templates"]:
        result[day_template["day_id"]] = {}
        for pattern in day_template["required_patterns"]:
            result[day_template["day_id"]][pattern] = [
                {
                    "exercise_id": int(row["exercise_id"]),
                    "name": row["name"],
                    "equipment": row["equipment"],
                    "priority_score": int(row["priority_score"]),
                }
                for row in exercise_candidates(inputs, day_template["focus"], pattern)
            ]
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
