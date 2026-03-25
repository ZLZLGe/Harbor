from pathlib import Path

import pandas as pd


DATA_DIR = Path("/root/mine_inputs")
OUTPUT_FILE = Path("/root/mine_repeater_events.csv")
METHOD_FILE = DATA_DIR / "candidate_repeater_template_matching.csv"
BLAST_FILE = DATA_DIR / "blast_windows.csv"


def build_expected() -> pd.DataFrame:
    catalog = pd.read_csv(METHOD_FILE)
    blasts = pd.read_csv(BLAST_FILE)
    catalog["time"] = pd.to_datetime(catalog["time"])
    blasts["start_time"] = pd.to_datetime(blasts["start_time"])
    blasts["end_time"] = pd.to_datetime(blasts["end_time"])

    keep_mask = pd.Series(True, index=catalog.index)
    for blast in blasts.itertuples(index=False):
        keep_mask &= ~catalog["time"].between(blast.start_time, blast.end_time, inclusive="both")
    catalog = catalog.loc[keep_mask].copy()

    chosen_groups = []
    for _, family_frame in catalog.groupby("repeater_family", sort=False):
        family_frame = family_frame.sort_values("time")
        chosen_rows = []
        for row in family_frame.itertuples(index=False):
            if not chosen_rows:
                chosen_rows.append(row)
                continue
            previous = chosen_rows[-1]
            gap = (row.time - previous.time).total_seconds()
            if gap <= 1.5:
                if row.correlation_peak > previous.correlation_peak:
                    chosen_rows[-1] = row
                elif row.correlation_peak == previous.correlation_peak:
                    if row.sensor_count > previous.sensor_count:
                        chosen_rows[-1] = row
                    elif row.sensor_count == previous.sensor_count and row.time < previous.time:
                        chosen_rows[-1] = row
            else:
                chosen_rows.append(row)
        chosen_groups.append(pd.DataFrame(chosen_rows))

    expected = pd.concat(chosen_groups, ignore_index=True).sort_values("time").reset_index(drop=True)
    expected["time"] = expected["time"].dt.strftime("%Y-%m-%dT%H:%M:%S")
    expected["method_family"] = "template_matching"
    return expected[
        [
            "time",
            "repeater_family",
            "template_id",
            "sensor_count",
            "correlation_peak",
            "method_family",
        ]
    ]


def test_output_exists():
    assert OUTPUT_FILE.exists(), f"missing output file: {OUTPUT_FILE}"


def test_schema_and_selected_method():
    produced = pd.read_csv(OUTPUT_FILE)
    assert list(produced.columns) == [
        "time",
        "repeater_family",
        "template_id",
        "sensor_count",
        "correlation_peak",
        "method_family",
    ]
    parsed_times = pd.to_datetime(produced["time"])
    assert parsed_times.is_monotonic_increasing, "final detections must be sorted by time"
    assert set(produced["method_family"]) == {"template_matching"}


def test_blast_windows_removed():
    produced = pd.read_csv(OUTPUT_FILE)
    produced["time"] = pd.to_datetime(produced["time"])
    blasts = pd.read_csv(BLAST_FILE)
    blasts["start_time"] = pd.to_datetime(blasts["start_time"])
    blasts["end_time"] = pd.to_datetime(blasts["end_time"])
    for blast in blasts.itertuples(index=False):
        overlapping = produced["time"].between(blast.start_time, blast.end_time, inclusive="both")
        assert not overlapping.any(), f"blast-window detection remained during {blast.blast_name}"


def test_matches_expected_template_output():
    produced = pd.read_csv(OUTPUT_FILE)
    expected = build_expected()
    pd.testing.assert_frame_equal(
        produced.reset_index(drop=True),
        expected.reset_index(drop=True),
        check_dtype=False,
    )


def test_no_same_family_duplicates_within_one_point_five_seconds():
    produced = pd.read_csv(OUTPUT_FILE)
    produced["time"] = pd.to_datetime(produced["time"])
    for family, family_frame in produced.groupby("repeater_family"):
        gaps = family_frame.sort_values("time")["time"].diff().dropna().dt.total_seconds()
        assert (gaps > 1.5).all(), f"duplicate detections remain for {family}"
