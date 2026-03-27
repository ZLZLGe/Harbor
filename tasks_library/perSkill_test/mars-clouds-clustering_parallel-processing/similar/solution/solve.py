#!/usr/bin/env python3
import csv
import json
from itertools import product
from pathlib import Path

from joblib import Parallel, delayed


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


def pareto_frontier(rows):
    return [row for row in rows if not is_dominated(row, rows)]


def main():
    scenes = json.loads(Path("/root/data/scenes.json").read_text())

    min_samples_grid = [3, 4, 5, 6]
    epsilon_grid = [4, 8, 12, 16]
    shape_weight_grid = [0.9, 1.1, 1.3, 1.5]

    grid = list(product(min_samples_grid, epsilon_grid, shape_weight_grid))
    evaluated = Parallel(n_jobs=-1, backend="loky")(
        delayed(evaluate_combo)(params, scenes) for params in grid
    )
    rows = [row for row in evaluated if row is not None]
    frontier = pareto_frontier(rows)
    frontier.sort(key=lambda x: (-x["F1"], x["delta"], x["min_samples"], x["epsilon"], x["shape_weight"]))

    output_path = Path("/outputs/similar_frontier.csv")
    with output_path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["F1", "delta", "min_samples", "epsilon", "shape_weight"],
        )
        writer.writeheader()
        for row in frontier:
            writer.writerow(row)


if __name__ == "__main__":
    main()
