#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "/root/workspace")

from wyckoff_constraint_solver import solve_wyckoff_constraint_cases


EXPECTED = {
    "orbit_alpha": {
        "parameters": {"x": "1/3", "y": "-1/4"},
        "canonical_representative": ["1/3", "3/4", "1/6"],
        "orbit_multiplicity": 4,
    },
    "orbit_beta": {
        "parameters": {"x": "1/2"},
        "canonical_representative": ["1/2", "0", "1/4"],
        "orbit_multiplicity": 2,
    },
    "orbit_gamma": {
        "parameters": {"x": "1/3", "y": "5/8", "z": "7/8"},
        "canonical_representative": ["5/6", "5/8", "7/8"],
        "orbit_multiplicity": 6,
    },
    "orbit_delta": {
        "parameters": {"x": "1/4", "z": "7/12"},
        "canonical_representative": ["1/4", "5/12", "7/12"],
        "orbit_multiplicity": 4,
    },
}


def main() -> int:
    input_path = "/root/data/wyckoff_constraint_cases.json"
    results = solve_wyckoff_constraint_cases(input_path)
    assert results == EXPECTED, f"unexpected solver output: {results}"

    subprocess.run(["python3", "/root/workspace/wyckoff_constraint_solver.py"], check=True)
    output_path = Path("/root/workspace/wyckoff_constraint_results.json")
    assert output_path.exists(), "script mode did not create the output JSON file"
    written = json.loads(output_path.read_text())
    assert written == EXPECTED, f"unexpected written JSON: {written}"

    os.makedirs("/logs/verifier", exist_ok=True)
    with open("/logs/verifier/reward.txt", "w", encoding="utf-8") as handle:
        handle.write("1.00\n")

    print("All tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
