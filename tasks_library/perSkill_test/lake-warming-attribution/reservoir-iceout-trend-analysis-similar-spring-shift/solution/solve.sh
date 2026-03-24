#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
import os
from collections import Counter
from math import erf, sqrt


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


rows = []
with open("/root/data/reservoir_ice_out.csv", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        rows.append(
            {
                "season_year": int(row["season_year"]),
                "ice_out_day_of_year": float(row["ice_out_day_of_year"]),
            }
        )

rows.sort(key=lambda row: row["season_year"])
series = [row["ice_out_day_of_year"] for row in rows]

slope = sen_slope(series)
p_value = mann_kendall_p_value(series)

if slope < 0:
    direction = "earlier"
elif slope > 0:
    direction = "later"
else:
    direction = "no_change"

os.makedirs("/root/output", exist_ok=True)
with open("/root/output/ice_out_trend.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["sen_slope_days_per_year", "p_value", "shift_direction"])
    writer.writerow([f"{slope:.3f}", f"{p_value:.4f}", direction])
PY
