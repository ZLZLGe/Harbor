#!/bin/bash
set -e

python3 <<'PYTHON'
import csv
import os
from collections import Counter
from math import erf, sqrt


INPUT_PATH = "/root/data/rail_reliability_yearly.csv"
OUTPUT_PATH = "/root/output/reliability_metric_shift.csv"
METRICS = ["late_departure_rate_pct", "missed_connection_rate_pct"]


def sen_slope(values):
    slopes = []
    for i in range(len(values) - 1):
        for j in range(i + 1, len(values)):
            slopes.append((values[j] - values[i]) / (j - i))
    slopes.sort()
    mid = len(slopes) // 2
    if len(slopes) % 2 == 1:
        return slopes[mid]
    return (slopes[mid - 1] + slopes[mid]) / 2


def mann_kendall_p_value(values):
    s = 0
    n = len(values)
    for i in range(n - 1):
        for j in range(i + 1, n):
            if values[j] > values[i]:
                s += 1
            elif values[j] < values[i]:
                s -= 1

    counts = Counter(values)
    var_s = n * (n - 1) * (2 * n + 5)
    for tied_count in counts.values():
        if tied_count > 1:
            var_s -= tied_count * (tied_count - 1) * (2 * tied_count + 5)
    var_s /= 18

    if s > 0:
        z = (s - 1) / sqrt(var_s)
    elif s < 0:
        z = (s + 1) / sqrt(var_s)
    else:
        z = 0.0

    cdf = 0.5 * (1 + erf(abs(z) / sqrt(2)))
    return 2 * (1 - cdf)


with open(INPUT_PATH, newline="") as f:
    rows = list(csv.DictReader(f))

rows.sort(key=lambda row: int(row["service_year"]))

metric_results = []
for metric_name in METRICS:
    values = [float(row[metric_name]) for row in rows]
    metric_results.append(
        {
            "metric_name": metric_name,
            "slope": sen_slope(values),
            "p_value": mann_kendall_p_value(values),
        }
    )

metric_results.sort(key=lambda item: (-item["slope"], item["metric_name"]))
winner = metric_results[0]

os.makedirs("/root/output", exist_ok=True)
with open(OUTPUT_PATH, "w", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["metric_name", "sen_slope_pct_points_per_year", "p_value"],
    )
    writer.writeheader()
    writer.writerow(
        {
            "metric_name": winner["metric_name"],
            "sen_slope_pct_points_per_year": f"{winner['slope']:.3f}",
            "p_value": f"{winner['p_value']:.4f}",
        }
    )
PYTHON
