#!/usr/bin/env python3
import csv
import json
from itertools import product
from pathlib import Path

OUTPUT = Path("/outputs/similar_frontier.csv")
SCENES = Path("/root/data/scenes.json")


def score_scene(scene, min_samples, epsilon, shape_weight):
    ms_gap = abs(min_samples - scene["best_min_samples"])
    eps_gap = abs(epsilon - scene["best_epsilon"])
    sw_gap = abs(shape_weight - scene["best_shape_weight"])

    penalty = (0.06 * ms_gap) + (0.018 * eps_gap) + (0.22 * sw_gap)
    f1 = max(0.0, scene["base_f1"] - penalty - scene["noise"] * 0.03)

    delta = (
        scene["base_delta"]
        + (1.9 * ms_gap)
        + (0.75 * eps_gap)
        + (6.5 * sw_gap)
        + (1.2 * scene["noise"])
    )
    return f1, delta


def evaluate_combo(params, scenes):
    min_samples, epsilon, shape_weight = params
    f1_vals = []
    delta_vals = []
    for scene in scenes:
        f1, delta = score_scene(scene, min_samples, epsilon, shape_weight)
        f1_vals.append(f1)
        delta_vals.append(delta)

    mean_f1 = sum(f1_vals) / len(f1_vals)
    mean_delta = sum(delta_vals) / len(delta_vals)
    if mean_f1 <= 0.58:
        return None

    return {
        "F1": round(mean_f1, 5),
        "delta": round(mean_delta, 5),
        "min_samples": int(min_samples),
        "epsilon": int(epsilon),
        "shape_weight": round(shape_weight, 1),
    }


def is_dominated(candidate, others):
    for other in others:
        if other is candidate:
            continue
        if (
            other["F1"] >= candidate["F1"]
            and other["delta"] <= candidate["delta"]
            and (
                other["F1"] > candidate["F1"]
                or other["delta"] < candidate["delta"]
            )
        ):
            return True
    return False


def expected_frontier():
    scenes = json.loads(SCENES.read_text())
    grid = product([3, 4, 5, 6], [4, 8, 12, 16], [0.9, 1.1, 1.3, 1.5])
    evaluated = [evaluate_combo(params, scenes) for params in grid]
    rows = [row for row in evaluated if row is not None]
    frontier = [row for row in rows if not is_dominated(row, rows)]
    frontier.sort(key=lambda x: (-x["F1"], x["delta"], x["min_samples"], x["epsilon"], x["shape_weight"]))
    return frontier


def load_actual_rows():
    with OUTPUT.open(newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            rows.append(
                {
                    "F1": round(float(row["F1"]), 5),
                    "delta": round(float(row["delta"]), 5),
                    "min_samples": int(row["min_samples"]),
                    "epsilon": int(row["epsilon"]),
                    "shape_weight": round(float(row["shape_weight"]), 1),
                }
            )
    return rows


def main():
    assert OUTPUT.exists(), "missing /outputs/similar_frontier.csv"
    expected = expected_frontier()
    actual = load_actual_rows()
    assert len(actual) > 0, "frontier CSV is empty"
    assert actual == expected, f"frontier mismatch\nexpected={expected}\nactual={actual}"


if __name__ == "__main__":
    main()
