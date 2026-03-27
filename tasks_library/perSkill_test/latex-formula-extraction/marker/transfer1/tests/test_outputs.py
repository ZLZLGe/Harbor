import json
from pathlib import Path

OUTPUT = Path('/root/transfer1_formula_ledger.json')
EXPECTED = Path('/root/input/expected_transfer1.json')


def main() -> None:
    assert OUTPUT.exists(), f'missing output file: {OUTPUT}'
    assert EXPECTED.exists(), f'missing expected file: {EXPECTED}'

    actual = json.loads(OUTPUT.read_text(encoding='utf-8'))
    expected = json.loads(EXPECTED.read_text(encoding='utf-8'))

    assert actual == expected, f'ledger mismatch\nexpected={expected}\nactual={actual}'


if __name__ == '__main__':
    main()
