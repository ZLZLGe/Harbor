import csv
from pathlib import Path

EXPECTED = Path("/root/expected_transfer2_formula_metrics.csv")
ACTUAL = Path("/root/transfer2_formula_metrics.csv")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    assert EXPECTED.exists(), f"missing expected reference: {EXPECTED}"
    assert ACTUAL.exists(), f"missing output: {ACTUAL}"

    expected_raw = EXPECTED.read_text(encoding="utf-8").strip()
    actual_raw = ACTUAL.read_text(encoding="utf-8").strip()
    assert actual_raw == expected_raw, "metrics CSV mismatch"

    rows = read_csv(ACTUAL)
    assert len(rows) == 5, f"expected 5 rows, got {len(rows)}"
    assert rows[-1]["status"] == "corrected", "last row must be corrected"
    for row in rows:
        assert row["contains_greek"] in {"yes", "no"}, f"invalid contains_greek: {row['contains_greek']}"


if __name__ == "__main__":
    main()
