from pathlib import Path

EXPECTED = Path("/root/expected_similar_formula_lines.md")
ACTUAL = Path("/root/similar_formula_lines.md")


def _lines(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    assert EXPECTED.exists(), f"missing expected reference: {EXPECTED}"
    assert ACTUAL.exists(), f"missing output: {ACTUAL}"

    expected_lines = _lines(EXPECTED)
    actual_lines = _lines(ACTUAL)

    assert actual_lines == expected_lines, "formula lines do not match expected normalized sequence"
    assert len(actual_lines) == 5, f"expected 5 formula lines, got {len(actual_lines)}"


if __name__ == "__main__":
    main()
