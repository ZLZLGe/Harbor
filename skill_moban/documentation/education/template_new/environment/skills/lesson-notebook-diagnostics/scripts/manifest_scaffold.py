from __future__ import annotations

import json


REQUIRED = [
    "What we're analyzing",
    "Understand the event data",
    "Build the session funnel",
    "Compare quiz outcomes",
    "Spot metric definition traps",
    "Practice",
    "Wrap up",
]


def main() -> int:
    payload = {
        "lesson_info": {
            "title": "New Analyst Workshop",
            "audience": "new data analysts",
        },
        "sections": [
            {
                "title": title,
                "learning_goal": "",
                "uses_files": [],
                "has_exercise": title == "Practice",
            }
            for title in REQUIRED
        ],
        "key_metrics": [],
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
