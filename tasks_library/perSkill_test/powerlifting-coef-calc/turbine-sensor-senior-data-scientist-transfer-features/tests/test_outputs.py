import csv
import math
import os
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path


LOG_FILE = os.environ.get("LOG_FILE", "/root/data/turbine_sensor_logs.csv")
LABEL_FILE = os.environ.get("LABEL_FILE", "/root/data/maintenance_labels.csv")
OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "/root/results/turbine_features.csv")
TS_FORMAT = "%Y-%m-%dT%H:%M"
FLOAT_TOL = 1e-9
HEADER = [
    "turbine_id",
    "snapshot_ts",
    "split",
    "failure_within_24h",
    "rpm_mean_60m",
    "rpm_std_60m",
    "temp_mean_180m",
    "temp_slope_180m",
    "vibration_std_60m",
    "pressure_missing_rate_180m",
    "alarm_count_180m",
]


def parse_ts(value):
    return datetime.strptime(value, TS_FORMAT)


def parse_float(value):
    return None if value == "" else float(value)


def mean(values):
    return sum(values) / len(values) if values else 0.0


def pop_std(values):
    if not values:
        return 0.0
    mu = mean(values)
    return math.sqrt(sum((value - mu) ** 2 for value in values) / len(values))


def slope(points):
    if len(points) < 2:
        return 0.0
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    x_bar = mean(xs)
    y_bar = mean(ys)
    denom = sum((x - x_bar) ** 2 for x in xs)
    if denom == 0:
        return 0.0
    numer = sum((x - x_bar) * (y - y_bar) for x, y in points)
    return numer / denom


def load_logs():
    logs = defaultdict(dict)
    with open(LOG_FILE, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            ts = parse_ts(row["event_ts"])
            logs[row["turbine_id"]][ts] = {
                "rpm": parse_float(row["rpm"]),
                "temp_c": parse_float(row["temp_c"]),
                "vibration_mm_s": parse_float(row["vibration_mm_s"]),
                "pressure_kpa": parse_float(row["pressure_kpa"]),
                "alarm_flag": int(row["alarm_flag"]),
            }
    return logs


def expected_rows():
    logs = load_logs()
    rows = []
    with open(LABEL_FILE, newline="", encoding="utf-8") as handle:
        for label in csv.DictReader(handle):
            turbine_logs = logs[label["turbine_id"]]
            snapshot_ts = parse_ts(label["snapshot_ts"])
            sixty_start = snapshot_ts - timedelta(minutes=59)
            one_eighty_start = snapshot_ts - timedelta(minutes=179)

            sixty_rows = []
            one_eighty_rows = []
            pressure_missing = 0
            ts = one_eighty_start
            while ts <= snapshot_ts:
                record = turbine_logs.get(ts)
                if record is None or record["pressure_kpa"] is None:
                    pressure_missing += 1
                if record is not None:
                    one_eighty_rows.append((ts, record))
                    if ts >= sixty_start:
                        sixty_rows.append((ts, record))
                ts += timedelta(minutes=1)

            rpm_values = [record["rpm"] for _, record in sixty_rows if record["rpm"] is not None]
            temp_values = [record["temp_c"] for _, record in one_eighty_rows if record["temp_c"] is not None]
            temp_points = [
                (int((ts - one_eighty_start).total_seconds() // 60), record["temp_c"])
                for ts, record in one_eighty_rows
                if record["temp_c"] is not None
            ]
            vibration_values = [
                record["vibration_mm_s"]
                for _, record in sixty_rows
                if record["vibration_mm_s"] is not None
            ]
            alarm_count = sum(record["alarm_flag"] for _, record in one_eighty_rows)

            rows.append(
                {
                    "turbine_id": label["turbine_id"],
                    "snapshot_ts": label["snapshot_ts"],
                    "split": label["split"],
                    "failure_within_24h": str(int(label["failure_within_24h"])),
                    "rpm_mean_60m": mean(rpm_values),
                    "rpm_std_60m": pop_std(rpm_values),
                    "temp_mean_180m": mean(temp_values),
                    "temp_slope_180m": slope(temp_points),
                    "vibration_std_60m": pop_std(vibration_values),
                    "pressure_missing_rate_180m": pressure_missing / 180.0,
                    "alarm_count_180m": int(alarm_count),
                }
            )

    rows.sort(key=lambda row: (row["turbine_id"], row["snapshot_ts"]))
    return rows


def actual_rows():
    with open(OUTPUT_FILE, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == HEADER
        return list(reader)


def assert_close(actual, expected):
    assert math.isclose(float(actual), expected, rel_tol=0.0, abs_tol=FLOAT_TOL), (
        actual,
        expected,
    )


def test_output_exists():
    assert Path(OUTPUT_FILE).exists(), "missing output CSV"


def test_schema_and_row_order():
    rows = actual_rows()
    expected = expected_rows()
    assert len(rows) == len(expected)

    observed_keys = [(row["turbine_id"], row["snapshot_ts"]) for row in rows]
    expected_keys = [(row["turbine_id"], row["snapshot_ts"]) for row in expected]
    assert observed_keys == expected_keys


def test_feature_values():
    rows = actual_rows()
    expected = expected_rows()

    for actual, want in zip(rows, expected):
        assert actual["turbine_id"] == want["turbine_id"]
        assert actual["snapshot_ts"] == want["snapshot_ts"]
        assert actual["split"] == want["split"]
        assert actual["failure_within_24h"] == want["failure_within_24h"]
        assert_close(actual["rpm_mean_60m"], want["rpm_mean_60m"])
        assert_close(actual["rpm_std_60m"], want["rpm_std_60m"])
        assert_close(actual["temp_mean_180m"], want["temp_mean_180m"])
        assert_close(actual["temp_slope_180m"], want["temp_slope_180m"])
        assert_close(actual["vibration_std_60m"], want["vibration_std_60m"])
        assert_close(
            actual["pressure_missing_rate_180m"],
            want["pressure_missing_rate_180m"],
        )
        assert int(actual["alarm_count_180m"]) == want["alarm_count_180m"]


def test_no_future_leakage_signal():
    rows = {row["snapshot_ts"]: row for row in actual_rows() if row["turbine_id"] == "T-100"}
    expected = {row["snapshot_ts"]: row for row in expected_rows() if row["turbine_id"] == "T-100"}

    early_snapshot = "2025-02-01T03:59"
    late_snapshot = "2025-02-01T04:59"

    assert_close(rows[early_snapshot]["temp_mean_180m"], expected[early_snapshot]["temp_mean_180m"])
    assert_close(rows[late_snapshot]["temp_mean_180m"], expected[late_snapshot]["temp_mean_180m"])

    early_value = float(rows[early_snapshot]["temp_mean_180m"])
    late_value = float(rows[late_snapshot]["temp_mean_180m"])
    assert late_value - early_value > 10.0
