from __future__ import annotations

import json

from planner_core import food_candidates, load_inputs


def main() -> None:
    inputs = load_inputs()
    payload = {}
    for day_template in inputs["rules"]["nutrition_rules"]["plan_day_templates"]:
        payload[day_template["plan_day"]] = {}
        for slot, role_specs in day_template["slot_roles"].items():
            payload[day_template["plan_day"]][slot] = {}
            for role_spec in role_specs:
                role = role_spec["role"]
                payload[day_template["plan_day"]][slot][role] = [
                    {
                        "food_id": int(row["food_id"]),
                        "description": row["description"],
                        "priority_score": float(row["priority_score"]),
                    }
                    for row in food_candidates(inputs, slot, role)
                ]
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
