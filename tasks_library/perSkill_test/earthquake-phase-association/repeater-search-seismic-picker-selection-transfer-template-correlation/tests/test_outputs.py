import csv
import os
from datetime import datetime


DATA_DIR = os.environ.get("DATA_DIR", "/root/data")
OUTPUT_CSV = os.environ.get("OUTPUT_CSV", "/root/repeater_detections.csv")
SEED_CATALOG = os.path.join(DATA_DIR, "seed_catalog.csv")

REQUIRED_COLUMNS = {"detection_time", "matched_family", "score"}
EXPECTED = [
    ("2021-11-03T12:00:48.000", "A"),
    ("2021-11-03T12:01:34.500", "A"),
    ("2021-11-03T12:02:01.000", "B"),
    ("2021-11-03T12:02:29.500", "A"),
    ("2021-11-03T12:02:47.000", "B"),
]
TOLERANCE_SEC = 0.15


def load_output_rows():
    assert os.path.exists(OUTPUT_CSV), f"Missing output file: {OUTPUT_CSV}"
    with open(OUTPUT_CSV, newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - fieldnames
        assert not missing, f"Output is missing required columns: {sorted(missing)}"
        rows = []
        for row in reader:
            parsed = dict(row)
            parsed["detection_dt"] = datetime.fromisoformat(row["detection_time"])
            parsed["score_float"] = float(row["score"])
            rows.append(parsed)
    assert rows, "repeater_detections.csv is empty"
    return rows


def load_seed_times():
    with open(SEED_CATALOG, newline="") as f:
        reader = csv.DictReader(f)
        return [datetime.fromisoformat(row["seed_time"]) for row in reader]


def find_match(rows, target_time, target_family):
    best = None
    for row in rows:
        if row["matched_family"] != target_family:
            continue
        delta = abs((row["detection_dt"] - target_time).total_seconds())
        if delta <= TOLERANCE_SEC and (best is None or delta < best[0]):
            best = (delta, row)
    return None if best is None else best[1]


def main():
    rows = load_output_rows()
    seed_times = load_seed_times()

    assert len(rows) == len(EXPECTED), f"Expected {len(EXPECTED)} detections, got {len(rows)}"
    assert rows == sorted(rows, key=lambda row: row["detection_dt"]), "Rows must be sorted by detection_time"

    for row in rows:
        assert row["matched_family"] in {"A", "B"}, f"Unexpected family: {row['matched_family']}"
        assert 0.0 <= row["score_float"] <= 1.0, f"Score out of range: {row['score']}"
        assert row["score_float"] >= 0.6, f"Score too low: {row['score']}"
        assert all(abs((row["detection_dt"] - seed_time).total_seconds()) > 0.75 for seed_time in seed_times), (
            f"Seed event should not be reported again: {row['detection_time']}"
        )

    matched_rows = []
    for time_str, family in EXPECTED:
        target_time = datetime.fromisoformat(time_str)
        match = find_match(rows, target_time, family)
        assert match is not None, f"Missing expected detection near {time_str} for family {family}"
        matched_rows.append(match)

    assert len({row["detection_time"] for row in matched_rows}) == len(EXPECTED), "Detections are duplicated or ambiguous"

    print("Verified repeater detections:")
    for row in rows:
        print(f"{row['detection_time']} {row['matched_family']} score={row['score']}")


if __name__ == "__main__":
    main()
