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


def expected_winner():
    grouped = defaultdict(list)
    with open("/root/data/urban_pm25_observations.csv", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            year = int(row["observation_date"][:4])
            grouped[(row["site_id"], year)].append(float(row["pm25_ug_m3"]))

    annual = defaultdict(list)
    for (site_id, year), values in grouped.items():
        annual_high = sum(sorted(values)[-3:]) / 3
        annual[site_id].append((year, annual_high))

    candidates = []
    for site_id, series in annual.items():
        series.sort(key=lambda item: item[0])
        values = [value for _, value in series]
        slope = sen_slope(values)
        p_value = mann_kendall_p_value(values)
        if slope < 0 and p_value < 0.05:
            candidates.append(
                {
                    "site_id": site_id,
                    "slope": round(slope, 3),
                    "p_value": round(p_value, 4),
                    "years_used": len(values),
                }
            )

    candidates.sort(key=lambda item: (item["slope"], item["site_id"]))
    return candidates[0]


class TestUrbanPm25DeclineLeader:
    def test_output_exists(self):
        assert os.path.exists("/root/output/pm25_decline_leader.csv"), (
            "pm25_decline_leader.csv not found"
        )

    def test_output_schema_and_values(self):
        expected = expected_winner()

        with open("/root/output/pm25_decline_leader.csv", newline="") as f:
            reader = csv.DictReader(f)
            assert reader.fieldnames == [
                "site_id",
                "sen_slope_peak_pm25_per_year",
                "p_value",
                "years_used",
            ]
            rows = list(reader)

        assert len(rows) == 1, f"Expected exactly one result row, got {len(rows)}"
        row = rows[0]

        assert row["site_id"] == expected["site_id"]
        assert abs(float(row["sen_slope_peak_pm25_per_year"]) - expected["slope"]) <= 0.0005
        assert abs(float(row["p_value"]) - expected["p_value"]) <= 0.00005
        assert int(row["years_used"]) == expected["years_used"]
