from datetime import timedelta
from pathlib import Path

import pandas as pd


INPUT_PATH = Path("/root/cold_chain_monitor_book")
OUTPUT_PATH = Path("/root/cold_chain_breaches.csv")
EXPECTED_COLUMNS = ["batch_id", "route_id", "breach_minutes", "breach_type"]
ALLOWED_TYPES = {"cumulative_over_limit", "recovery_timeout", "sensor_missing"}


def minutes(delta):
    return int(delta.total_seconds() // 60)


def build_intervals(sensor_rows, window_start, window_end, max_gap_minutes):
    intervals = []
    gap_limit = timedelta(minutes=int(max_gap_minutes))

    for idx, row in enumerate(sensor_rows):
        reading_ts = row["reading_ts"]
        next_ts = sensor_rows[idx + 1]["reading_ts"] if idx + 1 < len(sensor_rows) else None
        effective_end = reading_ts + gap_limit if next_ts is None else min(next_ts, reading_ts + gap_limit)

        start = max(reading_ts, window_start)
        end = min(effective_end, window_end)
        if start < end:
            intervals.append((start, end, float(row["temperature_c"])))

    intervals.sort(key=lambda item: item[0])
    return intervals


def uncovered_minutes(intervals, window_start, window_end):
    cursor = window_start
    missing = 0

    for start, end, _temp in intervals:
        if end <= cursor:
            continue
        if start > cursor:
            missing += minutes(start - cursor)
            cursor = start
        if end > cursor:
            cursor = end

    if cursor < window_end:
        missing += minutes(window_end - cursor)

    return missing


def compute_expected():
    sheets = pd.read_excel(INPUT_PATH, sheet_name=None, engine="openpyxl")
    route_sla = sheets["Route SLA"].copy()
    trips = sheets["Trips"].copy()
    batch_map = sheets["Batch Map"].copy()
    sensor_log = sheets["Sensor Log"].copy()

    for frame, cols in (
        (trips, ["depart_ts", "arrive_ts"]),
        (batch_map, ["load_end_ts", "handoff_ts"]),
        (sensor_log, ["reading_ts"]),
    ):
        for column in cols:
            frame[column] = pd.to_datetime(frame[column])

    sla_by_route = route_sla.set_index("route_id").to_dict(orient="index")
    trips_by_id = trips.set_index("trip_id").to_dict(orient="index")

    sensor_log = sensor_log.sort_values(["sensor_id", "reading_ts"], kind="mergesort")
    readings_by_sensor = {}
    for sensor_id, group in sensor_log.groupby("sensor_id", sort=False):
        readings_by_sensor[sensor_id] = group.to_dict(orient="records")

    rows = []
    for batch in batch_map.to_dict(orient="records"):
        trip = trips_by_id[batch["trip_id"]]
        route_id = trip["route_id"]
        rules = sla_by_route[route_id]
        window_start = batch["load_end_ts"] + timedelta(minutes=int(rules["loading_grace_min"]))
        window_end = batch["handoff_ts"]

        intervals = build_intervals(
            readings_by_sensor.get(batch["sensor_id"], []),
            window_start,
            window_end,
            rules["max_gap_min"],
        )
        missing = uncovered_minutes(intervals, window_start, window_end)
        if missing > 0:
            rows.append(
                {
                    "batch_id": batch["batch_id"],
                    "route_id": route_id,
                    "breach_minutes": missing,
                    "breach_type": "sensor_missing",
                }
            )
            continue

        limit = float(rules["temp_limit_c"])
        cumulative_minutes = 0
        longest_timeout = 0
        episode_start = None

        for start, end, temperature in intervals:
            duration = minutes(end - start)
            if temperature > limit:
                cumulative_minutes += duration
                if episode_start is None:
                    episode_start = start
            elif episode_start is not None:
                longest_timeout = max(longest_timeout, minutes(start - episode_start))
                episode_start = None

        if episode_start is not None:
            longest_timeout = max(longest_timeout, minutes(window_end - episode_start))

        if cumulative_minutes > int(rules["cumulative_breach_limit_min"]):
            rows.append(
                {
                    "batch_id": batch["batch_id"],
                    "route_id": route_id,
                    "breach_minutes": cumulative_minutes,
                    "breach_type": "cumulative_over_limit",
                }
            )

        if longest_timeout > int(rules["recovery_limit_min"]):
            rows.append(
                {
                    "batch_id": batch["batch_id"],
                    "route_id": route_id,
                    "breach_minutes": longest_timeout,
                    "breach_type": "recovery_timeout",
                }
            )

    expected = pd.DataFrame(rows, columns=EXPECTED_COLUMNS)
    if expected.empty:
        return expected

    expected["breach_minutes"] = expected["breach_minutes"].astype(int)
    return expected.sort_values(["route_id", "batch_id", "breach_type"], kind="mergesort").reset_index(drop=True)


def test_output_exists():
    assert OUTPUT_PATH.exists(), "缺少输出文件 /root/cold_chain_breaches.csv"


def test_csv_schema_and_sort_order():
    actual = pd.read_csv(OUTPUT_PATH)

    assert list(actual.columns) == EXPECTED_COLUMNS, "CSV 列顺序不符合要求"
    assert set(actual["breach_type"]).issubset(ALLOWED_TYPES), "存在未声明的 breach_type"
    assert actual["breach_minutes"].map(lambda value: float(value).is_integer() and int(value) > 0).all()

    sorted_actual = actual.sort_values(["route_id", "batch_id", "breach_type"], kind="mergesort").reset_index(drop=True)
    pd.testing.assert_frame_equal(actual.reset_index(drop=True), sorted_actual)


def test_breach_rows_match_rules_defined_in_instruction():
    actual = pd.read_csv(OUTPUT_PATH)
    actual["breach_minutes"] = actual["breach_minutes"].astype(int)
    actual = actual[EXPECTED_COLUMNS].reset_index(drop=True)

    expected = compute_expected()
    pd.testing.assert_frame_equal(actual, expected)


def test_batches_with_sensor_missing_do_not_emit_other_types():
    actual = pd.read_csv(OUTPUT_PATH)
    missing_batches = set(actual.loc[actual["breach_type"] == "sensor_missing", "batch_id"])
    for batch_id in missing_batches:
        subset = actual.loc[actual["batch_id"] == batch_id, "breach_type"].tolist()
        assert subset == ["sensor_missing"], f"{batch_id} 命中缺测后不应再输出其他类别"
