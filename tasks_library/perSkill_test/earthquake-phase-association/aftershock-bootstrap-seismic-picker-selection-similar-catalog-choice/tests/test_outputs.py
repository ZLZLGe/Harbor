from pathlib import Path

import os

import pandas as pd


DATA_DIR = Path(os.environ.get("BOOTSTRAP_DATA_DIR", "/root/bootstrap_data"))
OUTPUT_FILE = Path(os.environ.get("BOOTSTRAP_OUTPUT_FILE", "/root/bootstrap_events.csv"))


def deduplicate(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["time"] = pd.to_datetime(frame["time"])
    chosen_rows = []
    for row in frame.sort_values("time").itertuples(index=False):
        if not chosen_rows:
            chosen_rows.append(row)
            continue
        previous = chosen_rows[-1]
        if (row.time - previous.time).total_seconds() <= 4:
            if row.supporting_stations > previous.supporting_stations:
                chosen_rows[-1] = row
            elif row.supporting_stations == previous.supporting_stations:
                if row.mean_pick_score > previous.mean_pick_score:
                    chosen_rows[-1] = row
                elif row.mean_pick_score == previous.mean_pick_score and row.time < previous.time:
                    chosen_rows[-1] = row
        else:
            chosen_rows.append(row)
    result = pd.DataFrame(chosen_rows)
    result["time"] = result["time"].dt.strftime("%Y-%m-%dT%H:%M:%S")
    result["method_family"] = "deep_learning"
    return result[["time", "supporting_stations", "mean_pick_score", "method_family"]]


def test_output_exists():
    assert OUTPUT_FILE.exists(), f"missing output file: {OUTPUT_FILE}"


def test_catalog_schema_and_order():
    catalog = pd.read_csv(OUTPUT_FILE)
    assert list(catalog.columns) == [
        "time",
        "supporting_stations",
        "mean_pick_score",
        "method_family",
    ]
    parsed_times = pd.to_datetime(catalog["time"])
    assert parsed_times.is_monotonic_increasing, "catalog must be sorted by time"
    assert set(catalog["method_family"]) == {"deep_learning"}


def test_catalog_matches_expected_candidate():
    produced = pd.read_csv(OUTPUT_FILE)
    expected_source = pd.read_csv(DATA_DIR / "candidate_catalog_deep_learning.csv")
    expected = deduplicate(expected_source)
    pd.testing.assert_frame_equal(produced.reset_index(drop=True), expected.reset_index(drop=True), check_dtype=False)


def test_no_duplicate_events_within_four_seconds():
    catalog = pd.read_csv(OUTPUT_FILE)
    times = pd.to_datetime(catalog["time"]).sort_values().reset_index(drop=True)
    gaps = times.diff().dropna().dt.total_seconds()
    assert (gaps > 4).all(), "duplicate detections within four seconds were not collapsed"
