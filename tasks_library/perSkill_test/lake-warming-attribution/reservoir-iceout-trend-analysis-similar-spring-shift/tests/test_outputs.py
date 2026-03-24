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


def expected_result():
    rows = []
    with open("/root/data/reservoir_ice_out.csv", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(
                (
                    int(row["season_year"]),
                    float(row["ice_out_day_of_year"]),
                )
            )

    rows.sort(key=lambda row: row[0])
    values = [row[1] for row in rows]
    slope = round(sen_slope(values), 3)
    p_value = round(mann_kendall_p_value(values), 4)
    direction = "earlier" if slope < 0 else "later" if slope > 0 else "no_change"
    return slope, p_value, direction


class TestReservoirIceOutTrend:
    def test_output_exists(self):
        assert os.path.exists("/root/output/ice_out_trend.csv"), "ice_out_trend.csv not found"

    def test_output_schema_and_values(self):
        expected_slope, expected_p_value, expected_direction = expected_result()

        with open("/root/output/ice_out_trend.csv", newline="") as f:
            reader = csv.DictReader(f)
            assert reader.fieldnames == [
                "sen_slope_days_per_year",
                "p_value",
                "shift_direction",
            ]
            rows = list(reader)

        assert len(rows) == 1, f"Expected exactly one result row, got {len(rows)}"
        row = rows[0]

        slope = float(row["sen_slope_days_per_year"])
        p_value = float(row["p_value"])
        direction = row["shift_direction"]

        assert abs(slope - expected_slope) <= 0.0005, (
            f"Expected slope {expected_slope}, got {slope}"
        )
        assert abs(p_value - expected_p_value) <= 0.00005, (
            f"Expected p-value {expected_p_value}, got {p_value}"
        )
        assert direction == expected_direction, (
            f"Expected shift_direction {expected_direction}, got {direction}"
        )
