from pathlib import Path

OUTPUT = Path('/root/transfer2_page_formula_counts.csv')
EXPECTED = Path('/root/input/expected_transfer2.csv')


def main() -> None:
    assert OUTPUT.exists(), f'missing output file: {OUTPUT}'
    assert EXPECTED.exists(), f'missing expected file: {EXPECTED}'

    actual = OUTPUT.read_text(encoding='utf-8').strip()
    expected = EXPECTED.read_text(encoding='utf-8').strip()
    assert actual == expected, f'csv mismatch\nexpected:\n{expected}\nactual:\n{actual}'


if __name__ == '__main__':
    main()
