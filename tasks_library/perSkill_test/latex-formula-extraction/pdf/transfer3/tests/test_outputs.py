from pathlib import Path

EXPECTED = Path("/root/expected_transfer3_formula_errata.md")
ACTUAL = Path("/root/transfer3_formula_errata.md")


def main() -> None:
    assert EXPECTED.exists(), f"missing expected reference: {EXPECTED}"
    assert ACTUAL.exists(), f"missing output: {ACTUAL}"

    expected = EXPECTED.read_text(encoding="utf-8").strip()
    actual = ACTUAL.read_text(encoding="utf-8").strip()

    assert actual == expected, "errata markdown mismatch"
    assert actual.startswith("# Formula Errata Brief"), "missing report title"
    assert "## Extracted Display Formulas" in actual, "missing extracted section"
    assert "## Syntax Fix" in actual, "missing syntax fix section"
    assert actual.count("\n1. $$") == 1, "expected numbered formula list"
    assert "- Corrected:" in actual, "missing corrected formula bullet"


if __name__ == "__main__":
    main()
