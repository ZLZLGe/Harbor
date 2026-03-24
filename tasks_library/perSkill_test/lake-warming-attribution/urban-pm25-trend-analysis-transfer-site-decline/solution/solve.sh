#!/bin/bash
set -e

python3 <<'PYTHON'
import csv
import os
from collections import Counter, defaultdict
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


measurements = defaultdict(list)
with open("/root/data/urban_pm25_observations.csv", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        year = int(row["observation_date"][:4])
        site_id = row["site_id"]
        measurements[(site_id, year)].append(float(row["pm25_ug_m3"]))

annual_series = defaultdict(list)
for (site_id, year), values in measurements.items():
    top_three_mean = sum(sorted(values)[-3:]) / 3
    annual_series[site_id].append((year, top_three_mean))

candidates = []
for site_id, series in annual_series.items():
    series.sort(key=lambda item: item[0])
    yearly_values = [value for _, value in series]
    slope = sen_slope(yearly_values)
    p_value = mann_kendall_p_value(yearly_values)
    if slope < 0 and p_value < 0.05:
        candidates.append((slope, site_id, p_value, len(yearly_values)))

candidates.sort(key=lambda item: (item[0], item[1]))
best_slope, best_site, best_p_value, years_used = candidates[0]

os.makedirs("/root/output", exist_ok=True)
with open("/root/output/pm25_decline_leader.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(
        ["site_id", "sen_slope_peak_pm25_per_year", "p_value", "years_used"]
    )
    writer.writerow(
        [best_site, f"{best_slope:.3f}", f"{best_p_value:.4f}", str(years_used)]
    )
PYTHON
