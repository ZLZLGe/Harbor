#!/usr/bin/env python3

import json
import os
from pathlib import Path

from evaluate import build_expected_solution, load_json

TASK_ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = Path(os.environ.get("DATA_FILE", "/data/puzzle_map_calibration/scenario.json"))
if not DATA_FILE.exists():
    DATA_FILE = TASK_ROOT / "environment" / "data" / "puzzle_map_calibration" / "scenario.json"

OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/output"))
if not OUTPUT_DIR.exists():
    OUTPUT_DIR = TASK_ROOT / "local_output"

OUTPUT_FILE = OUTPUT_DIR / "puzzle_map_calibration.json"
SCORE_DIR = Path(os.environ.get("SCORE_DIR", "/logs/verifier/scores"))


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    SCORE_DIR.mkdir(parents=True, exist_ok=True)

    assert_true(OUTPUT_FILE.exists(), f"Solution file not found: {OUTPUT_FILE}")

    with OUTPUT_FILE.open() as f:
        solution = json.load(f)

    payload = load_json(DATA_FILE)
    expected = build_expected_solution(payload)

    assert_true(isinstance(solution, dict), "Solution must be a JSON object")
    assert_true(isinstance(solution.get("scenario_id"), str), "scenario_id must be a string")
    assert_true(isinstance(solution.get("selected_patch_ids"), list), "selected_patch_ids must be a list")
    assert_true(isinstance(solution.get("patch_count"), int), "patch_count must be an integer")
    assert_true(isinstance(solution.get("patched_tiles"), list), "patched_tiles must be a list")
    assert_true(isinstance(solution.get("blueprint_legal"), bool), "blueprint_legal must be a boolean")
    assert_true(
        isinstance(solution.get("calibrated_adjacency_bonuses"), dict),
        "calibrated_adjacency_bonuses must be a dict",
    )
    assert_true(
        isinstance(solution.get("calibrated_total_adjacency"), (int, float)),
        "calibrated_total_adjacency must be numeric",
    )
    assert_true(
        solution["patch_count"] == len(solution["selected_patch_ids"]),
        "patch_count must equal the length of selected_patch_ids",
    )
    assert_true(
        len(solution["selected_patch_ids"]) == len(set(solution["selected_patch_ids"])),
        "selected_patch_ids must not contain duplicates",
    )
    assert_true(
        len(solution["patched_tiles"]) == len(solution["selected_patch_ids"]),
        "patched_tiles must align with selected_patch_ids",
    )

    for item in solution["patched_tiles"]:
        assert_true(isinstance(item, dict), "Each patched_tiles entry must be an object")
        assert_true(isinstance(item.get("tile"), list), "Each patched tile must include a tile list")
        assert_true(len(item["tile"]) == 2, "Each tile coordinate must have two integers")
        assert_true(all(isinstance(value, int) for value in item["tile"]), "Tile coordinates must be integers")
        assert_true(isinstance(item.get("changes"), dict), "Each patched tile must include a changes object")

    assert_true(
        solution["calibrated_total_adjacency"] == sum(solution["calibrated_adjacency_bonuses"].values()),
        "calibrated_total_adjacency must equal the sum of calibrated_adjacency_bonuses",
    )
    assert_true(
        solution == expected,
        "Output does not match the official minimal calibration result",
    )

    (SCORE_DIR / "puzzle_map_calibration.txt").write_text("1.0")
    print("All checks passed.")


if __name__ == "__main__":
    main()
