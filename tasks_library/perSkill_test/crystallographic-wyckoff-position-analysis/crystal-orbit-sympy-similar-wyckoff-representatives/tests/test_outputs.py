#!/usr/bin/env python3

import os
import sys
from pathlib import Path

sys.path.insert(0, "/root/workspace")

from wyckoff_orbit_solver import analyze_wyckoff_orbits


INPUT_PATH = Path("/root/orbit_cards/wyckoff_orbit_cards.json")
EXPECTED = {
    "cards": {
        "monoclinic_frame": {
            "framework_A": {
                "multiplicity": 4,
                "representative": ["1/8", "1/6", "1/5"],
                "positions": [
                    ["1/8", "1/6", "1/5"],
                    ["1/8", "1/3", "7/10"],
                    ["7/8", "2/3", "3/10"],
                    ["7/8", "5/6", "4/5"],
                ],
            },
            "channel_B": {
                "multiplicity": 4,
                "representative": ["0", "1/4", "1/4"],
                "positions": [
                    ["0", "1/4", "1/4"],
                    ["0", "1/4", "3/4"],
                    ["0", "3/4", "1/4"],
                    ["0", "3/4", "3/4"],
                ],
            },
            "axial_C": {
                "multiplicity": 2,
                "representative": ["0", "0", "0"],
                "positions": [
                    ["0", "0", "0"],
                    ["0", "1/2", "1/2"],
                ],
            },
        },
        "mirror_flip_net": {
            "surface_D": {
                "multiplicity": 2,
                "representative": ["0", "0", "1/7"],
                "positions": [
                    ["0", "0", "1/7"],
                    ["0", "0", "6/7"],
                ],
            },
            "center_E": {
                "multiplicity": 1,
                "representative": ["1/2", "1/2", "1/2"],
                "positions": [
                    ["1/2", "1/2", "1/2"],
                ],
            },
            "body_F": {
                "multiplicity": 4,
                "representative": ["2/9", "1/3", "5/12"],
                "positions": [
                    ["2/9", "1/3", "5/12"],
                    ["2/9", "2/3", "7/12"],
                    ["7/9", "1/3", "7/12"],
                    ["7/9", "2/3", "5/12"],
                ],
            },
        },
    }
}


def main():
    total_checks = 0
    passed_checks = 0

    result = analyze_wyckoff_orbits(str(INPUT_PATH))

    total_checks += 1
    if result == EXPECTED:
        print("Exact output check: PASSED")
        passed_checks += 1
    else:
        print("Exact output check: FAILED")
        print("Expected:")
        print(EXPECTED)
        print("Got:")
        print(result)

    total_checks += 1
    consistency_ok = True
    for card_orbits in result.get("cards", {}).values():
        for orbit_summary in card_orbits.values():
            positions = orbit_summary["positions"]
            if orbit_summary["multiplicity"] != len(positions):
                consistency_ok = False
            if orbit_summary["representative"] != positions[0]:
                consistency_ok = False

    if consistency_ok:
        print("Multiplicity/representative consistency: PASSED")
        passed_checks += 1
    else:
        print("Multiplicity/representative consistency: FAILED")

    score = passed_checks / total_checks if total_checks else 0.0
    os.makedirs("/logs/verifier", exist_ok=True)
    with open("/logs/verifier/reward.txt", "w", encoding="utf-8") as handle:
        handle.write(f"{score:.2f}\n")

    return 0 if passed_checks == total_checks else 1


if __name__ == "__main__":
    raise SystemExit(main())
