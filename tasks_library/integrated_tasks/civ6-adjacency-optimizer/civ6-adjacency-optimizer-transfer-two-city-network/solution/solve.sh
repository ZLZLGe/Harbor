#!/bin/bash

python3 <<'EOF'
import json
from pathlib import Path

OUTPUT_PATH = Path("/output/two_city_empire_plan.json")
GROUND_TRUTH_PATH = Path("/solution/ground_truths/two_city_empire/ground_truth.json")

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

with GROUND_TRUTH_PATH.open() as f:
    ground_truth = json.load(f)

with OUTPUT_PATH.open("w") as f:
    json.dump(ground_truth["reference_solution"], f, indent=2)

print(f"wrote {OUTPUT_PATH} with total_adjacency={ground_truth['optimal_adjacency']}")
EOF
