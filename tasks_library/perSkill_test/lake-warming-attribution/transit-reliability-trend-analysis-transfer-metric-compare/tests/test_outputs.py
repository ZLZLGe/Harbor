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


def expected_metric_results():
    with open(INPUT_PATH, newline="") as f:
        rows = list(csv.DictReader(f))

    rows.sort(key=lambda row: int(row["service_year"]))
    results = []
    for metric_name in METRICS:
        values = [float(row[metric_name]) for row in rows]
        results.append(
            {
                "metric_name": metric_name,
                "slope": round(sen_slope(values), 3),
                "p_value": round(mann_kendall_p_value(values), 4),
            }
        )

    results.sort(key=lambda item: (-item["slope"], item["metric_name"]))
    return results


class TestTransitReliabilityMetricShift:
    def test_output_exists(self):
        assert os.path.exists(OUTPUT_PATH), "reliability_metric_shift.csv not found"

    def test_output_schema_and_winner(self):
        expected_results = expected_metric_results()
        expected_winner = expected_results[0]
        runner_up = expected_results[1]

        with open(OUTPUT_PATH, newline="") as f:
            reader = csv.DictReader(f)
            assert reader.fieldnames == [
                "metric_name",
                "sen_slope_pct_points_per_year",
                "p_value",
            ]
            rows = list(reader)

        assert len(rows) == 1, f"Expected exactly one result row, got {len(rows)}"
        row = rows[0]

        metric_name = row["metric_name"]
        slope = float(row["sen_slope_pct_points_per_year"])
        p_value = float(row["p_value"])

        assert metric_name == expected_winner["metric_name"]
        assert abs(slope - expected_winner["slope"]) <= 0.0005
        assert abs(p_value - expected_winner["p_value"]) <= 0.00005
        assert expected_winner["slope"] > runner_up["slope"]

    def test_metric_name_is_limited_to_requested_kpis(self):
        with open(OUTPUT_PATH, newline="") as f:
            row = next(csv.DictReader(f))
        assert row["metric_name"] in METRICS
