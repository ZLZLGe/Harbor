import csv
from pathlib import Path

OUT = Path("/root/transfer1_cue_sheet.csv")

EXPECTED = [
    {"cue_title": "Tracing inner walls", "start_seconds": 0.0, "end_seconds": 73.0, "duration_seconds": 73.0},
    {"cue_title": "Break", "start_seconds": 73.0, "end_seconds": 78.0, "duration_seconds": 5.0},
    {"cue_title": "Continue tracing inner walls", "start_seconds": 78.0, "end_seconds": 314.0, "duration_seconds": 236.0},
    {"cue_title": "Remove doubled vertices", "start_seconds": 314.0, "end_seconds": 325.0, "duration_seconds": 11.0},
    {"cue_title": "Save", "start_seconds": 325.0, "end_seconds": 331.0, "duration_seconds": 6.0},
]


def to_float(value: str) -> float:
    return float(value.strip())


def main() -> None:
    assert OUT.exists(), f"missing output file: {OUT}"
    with OUT.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    assert rows, "CSV must contain data rows"
    assert len(rows) == len(EXPECTED), f"expected {len(EXPECTED)} rows, got {len(rows)}"
    assert rows[0].keys() == EXPECTED[0].keys(), f"unexpected columns: {list(rows[0].keys())}"

    previous_start = -1.0
    for got, exp in zip(rows, EXPECTED):
        assert got["cue_title"] == exp["cue_title"], f"cue title mismatch for {exp['cue_title']}"

        start = to_float(got["start_seconds"])
        end = to_float(got["end_seconds"])
        duration = to_float(got["duration_seconds"])

        assert start > previous_start, f"start times must be strictly increasing; got {start} after {previous_start}"
        assert start >= 0.0, f"negative start time for {exp['cue_title']}"
        assert end <= 331.0, f"end time exceeds excerpt for {exp['cue_title']}: {end}"
        assert end > start, f"end must be greater than start for {exp['cue_title']}"

        assert abs(start - exp["start_seconds"]) <= 5.0, f"start time too far off for {exp['cue_title']}"
        assert abs(end - exp["end_seconds"]) <= 5.0, f"end time too far off for {exp['cue_title']}"
        assert abs(duration - exp["duration_seconds"]) <= 5.0, f"duration too far off for {exp['cue_title']}"
        assert abs((end - start) - duration) <= 1.0, f"duration must match end-start for {exp['cue_title']}"

        previous_start = start


if __name__ == "__main__":
    main()
