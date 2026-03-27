#!/usr/bin/env python3
import csv
from itertools import product
from pathlib import Path

from joblib import Parallel, delayed


def load_events(path):
    events = []
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            events.append(
                {
                    "wind_speed": float(row["wind_speed"]),
                    "dust_index": float(row["dust_index"]),
                    "visibility_km": float(row["visibility_km"]),
                    "label": int(row["label"]),
                }
            )
    return events


def eval_config(config, events):
    wind_t, dust_t, cooldown = config

    tp = fp = fn = tn = 0
    for event in events:
        severity = 0.55 * event["wind_speed"] + 0.45 * event["dust_index"] - 4.0 * event["visibility_km"]
        threshold = 0.55 * wind_t + 0.45 * dust_t - cooldown * 0.25
        pred = 1 if severity >= threshold else 0

        if pred == 1 and event["label"] == 1:
            tp += 1
        elif pred == 1 and event["label"] == 0:
            fp += 1
        elif pred == 0 and event["label"] == 1:
            fn += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    false_alarm = fp / (fp + tn) if (fp + tn) else 0.0

    if precision < 0.45:
        return None

    return {
        "recall": round(recall, 5),
        "false_alarm": round(false_alarm, 5),
        "precision": round(precision, 5),
        "wind_threshold": int(wind_t),
        "dust_threshold": int(dust_t),
        "cooldown_min": int(cooldown),
    }


def is_dominated(candidate, others):
    for other in others:
        if other is candidate:
            continue
        if (
            other["recall"] >= candidate["recall"]
            and other["false_alarm"] <= candidate["false_alarm"]
            and (
                other["recall"] > candidate["recall"]
                or other["false_alarm"] < candidate["false_alarm"]
            )
        ):
            return True
    return False


def pareto_frontier(rows):
    return [row for row in rows if not is_dominated(row, rows)]


def main():
    events = load_events(Path("/root/data/events.csv"))
    grid = list(product([18, 22, 26, 30], [35, 45, 55, 65], [10, 20, 30]))

    evaluated = Parallel(n_jobs=-1, backend="loky")(
        delayed(eval_config)(config, events) for config in grid
    )
    rows = [row for row in evaluated if row is not None]
    frontier = pareto_frontier(rows)
    frontier.sort(
        key=lambda x: (
            -x["recall"],
            x["false_alarm"],
            -x["precision"],
            x["wind_threshold"],
            x["dust_threshold"],
            x["cooldown_min"],
        )
    )

    output_path = Path("/outputs/transfer3_alert_matrix.csv")
    with output_path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "recall",
                "false_alarm",
                "precision",
                "wind_threshold",
                "dust_threshold",
                "cooldown_min",
            ],
        )
        writer.writeheader()
        for row in frontier:
            writer.writerow(row)


if __name__ == "__main__":
    main()
