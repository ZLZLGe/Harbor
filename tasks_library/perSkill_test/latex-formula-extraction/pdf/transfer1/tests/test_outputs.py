import json
from pathlib import Path

EXPECTED = Path("/root/expected_transfer1_formula_catalog.json")
ACTUAL = Path("/root/transfer1_formula_catalog.json")


def main() -> None:
    assert EXPECTED.exists(), f"missing expected reference: {EXPECTED}"
    assert ACTUAL.exists(), f"missing output: {ACTUAL}"

    expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
    actual = json.loads(ACTUAL.read_text(encoding="utf-8"))

    assert actual == expected, "catalog JSON mismatch"
    assert actual.get("paper") == "latex_paper.pdf"

    entries = actual.get("entries")
    assert isinstance(entries, list) and len(entries) == 5, "entries must contain 5 formula records"

    ids = [entry.get("id") for entry in entries]
    assert ids == ["F1", "F2", "F3", "F4", "F5"], f"unexpected ids: {ids}"

    corrected = [entry for entry in entries if entry.get("status") == "corrected"]
    assert len(corrected) == 1, "must contain exactly one corrected entry"


if __name__ == "__main__":
    main()
