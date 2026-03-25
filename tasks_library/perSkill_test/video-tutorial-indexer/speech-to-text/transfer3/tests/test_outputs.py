import csv
from pathlib import Path

OUT = Path("/root/transfer3_closeout_schedule.tsv")

EXPECTED = [
    ("face_orientation_note", "Note on face orientation", 0.0, 39.0),
    ("save_as", "Save As", 39.0, 25.0),
    ("mixed_wall_types", "If you need thick and thin walls", 64.0, 17.0),
    ("great_job", "Great job!", 81.0, 15.0),
]


def main() -> None:
    assert OUT.exists(), f"missing output file: {OUT}"
    with OUT.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))

    assert rows, "TSV must contain data rows"
    assert len(rows) == len(EXPECTED), f"expected {len(EXPECTED)} rows, got {len(rows)}"

    previous_start = -1.0
    for got, expected in zip(rows, EXPECTED):
        card_id, label, exp_start, exp_gap = expected
        assert got["card_id"] == card_id, f"card_id mismatch for {card_id}"
        assert got["label"] == label, f"label mismatch for {card_id}"

        start = float(got["start_seconds"])
        gap = float(got["seconds_until_next"])

        assert start > previous_start, f"start_seconds must be strictly increasing; got {start} after {previous_start}"
        assert gap > 0.0, f"seconds_until_next must be positive for {card_id}"
        assert start + gap <= 96.0, f"row exceeds clip duration for {card_id}"
        assert abs(start - exp_start) <= 5.0, f"start_seconds too far off for {card_id}"
        assert abs(gap - exp_gap) <= 5.0, f"seconds_until_next too far off for {card_id}"

        previous_start = start


if __name__ == "__main__":
    main()
