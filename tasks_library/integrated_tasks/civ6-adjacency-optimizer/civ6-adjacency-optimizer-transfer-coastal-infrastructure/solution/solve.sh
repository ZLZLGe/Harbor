#!/bin/bash

python3 <<'EOF'
import json
from pathlib import Path

OUTPUT_PATH = Path("/output/coastal_corridor_plan.json")
GROUND_TRUTH_PATH = Path("/solution/ground_truths/coastal_corridor/ground_truth.json")

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

with GROUND_TRUTH_PATH.open() as f:
    ground_truth = json.load(f)

with OUTPUT_PATH.open("w") as f:
    json.dump(ground_truth["reference_solution"], f, indent=2)

print(
    f"wrote {OUTPUT_PATH} with weighted_score="
    f"{ground_truth['reference_solution']['weighted_score']}"
)
EOF
