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
with open("/root/data/assembly_quality_monthly.csv", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row["line_role"] != "flagship":
            continue
        rate = float(row["defects_found"]) / float(row["units_completed"]) * 100
        rows.append((row["month"], rate))

rows.sort(key=lambda item: item[0])
series = [rate for _, rate in rows]

slope = sen_slope(series)
p_value = mann_kendall_p_value(series)

if slope < 0:
    direction = "improving"
elif slope > 0:
    direction = "worsening"
else:
    direction = "stable"

os.makedirs("/root/output", exist_ok=True)
with open("/root/output/defect_rate_trend.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(
        ["sen_slope_pct_points_per_month", "p_value", "quality_direction"]
    )
    writer.writerow([f"{slope:.4f}", f"{p_value:.4f}", direction])
PY
