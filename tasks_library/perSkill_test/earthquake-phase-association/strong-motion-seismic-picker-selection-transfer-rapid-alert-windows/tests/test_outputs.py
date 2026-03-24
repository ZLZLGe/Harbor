import csv
import os
from datetime import datetime


OUTPUT_CSV = os.environ.get("OUTPUT_CSV", "/root/alert_windows.csv")
REFERENCE_CSV = os.environ.get("REFERENCE_CSV", "/tests/reference_windows.csv")
REQUIRED_COLUMNS = {"station", "window_start", "trigger_score"}


def load_rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def load_output_rows():
    assert os.path.exists(OUTPUT_CSV), f"Missing output file: {OUTPUT_CSV}"
    rows = load_rows(OUTPUT_CSV)
    assert rows, "alert_windows.csv is empty"

    fieldnames = set(rows[0].keys())
    missing = REQUIRED_COLUMNS - fieldnames
    assert not missing, f"Output is missing required columns: {sorted(missing)}"

    parsed = []
    for row in rows:
        parsed_row = dict(row)
        parsed_row["window_start_dt"] = datetime.fromisoformat(row["window_start"])
        parsed_row["trigger_score_float"] = float(row["trigger_score"])
        if "peak_accel" in row and row["peak_accel"]:
            parsed_row["peak_accel_float"] = float(row["peak_accel"])
        parsed.append(parsed_row)
    return parsed


def load_reference_rows():
    rows = load_rows(REFERENCE_CSV)
    parsed = []
    for row in rows:
        parsed_row = dict(row)
        parsed_row["expected_dt"] = datetime.fromisoformat(row["expected_window_start"])
        parsed_row["tolerance_sec"] = float(row["tolerance_sec"])
        parsed_row["max_latency_sec"] = float(row["max_latency_sec"])
        parsed.append(parsed_row)
    return parsed


def main():
    output_rows = load_output_rows()
    reference_rows = load_reference_rows()

    assert len(output_rows) == len(reference_rows), (
        f"Expected {len(reference_rows)} alert windows, got {len(output_rows)}"
    )
    assert output_rows == sorted(output_rows, key=lambda row: row["window_start_dt"]), (
        "Rows must be sorted by window_start"
    )

    seen_stations = set()
    for row in output_rows:
        assert row["station"] not in seen_stations, f"Duplicate station row: {row['station']}"
        seen_stations.add(row["station"])
        assert row["trigger_score_float"] >= 2.6, f"Trigger score too low for {row['station']}"
        if "peak_accel_float" in row:
            assert row["peak_accel_float"] >= 0.20, f"Peak acceleration too low for {row['station']}"

    reference_by_station = {row["station"]: row for row in reference_rows}
    assert seen_stations == set(reference_by_station), "Output stations do not match the provided station list"

    for row in output_rows:
        ref = reference_by_station[row["station"]]
        delta = (row["window_start_dt"] - ref["expected_dt"]).total_seconds()
        assert abs(delta) <= ref["tolerance_sec"], (
            f"{row['station']} window_start is too far from target: {delta:.3f}s"
        )
        assert delta >= -0.05, f"{row['station']} window_start is unrealistically early: {delta:.3f}s"
        assert delta <= ref["max_latency_sec"], f"{row['station']} window_start is too late: {delta:.3f}s"

    print("Verified alert windows:")
    for row in output_rows:
        print(f"{row['station']} {row['window_start']} trigger_score={row['trigger_score']}")


if __name__ == "__main__":
    main()
