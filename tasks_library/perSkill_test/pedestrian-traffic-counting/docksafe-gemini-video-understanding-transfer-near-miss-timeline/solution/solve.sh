#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import os

records = [
    {
        "video": "bay_alpha.avi",
        "timestamp": "00:06",
        "objects": ["forklift", "pedestrian"],
        "evidence": "The orange forklift skims past the person at the blue walkway with only a narrow gap.",
    },
    {
        "video": "bay_alpha.avi",
        "timestamp": "00:15",
        "objects": ["forklift", "handcart"],
        "evidence": "The forklift forks pass very close to the rolling handcart with almost no clearance.",
    },
    {
        "video": "bay_bravo.avi",
        "timestamp": "00:08",
        "objects": ["forklift", "pedestrian"],
        "evidence": "The forklift cuts across the walkway edge directly beside the pedestrian instead of yielding space.",
    },
    {
        "video": "bay_bravo.avi",
        "timestamp": "00:19",
        "objects": ["forklift", "handcart"],
        "evidence": "The forklift nose squeezes by the handcart corner with a very small side gap.",
    },
]

os.makedirs("/app/loading_dock", exist_ok=True)
with open("/app/loading_dock/near_miss_timeline.json", "w", encoding="utf-8") as handle:
    json.dump(records, handle, indent=2)
    handle.write("\n")
PY
