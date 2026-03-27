from pathlib import Path

OUTPUT = Path('/root/transfer3_formula_qc_report.md')
EXPECTED = Path('/root/input/expected_transfer3.md')


def main() -> None:
    assert OUTPUT.exists(), f'missing output file: {OUTPUT}'
    assert EXPECTED.exists(), f'missing expected file: {EXPECTED}'

    actual = OUTPUT.read_text(encoding='utf-8')
    expected = EXPECTED.read_text(encoding='utf-8')
    assert actual == expected, f'report mismatch\nexpected:\n{expected}\nactual:\n{actual}'


if __name__ == '__main__':
    main()
