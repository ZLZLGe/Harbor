import csv
from pathlib import Path

PRED_FILE = Path('/root/tutorial_minute_cards.csv')
EXPECTED_FILE = Path(__file__).parent / 'expected_minute_cards.csv'


def read_rows(path: Path):
    with path.open(newline='') as f:
        return list(csv.DictReader(f))


def main() -> None:
    assert PRED_FILE.exists(), f'missing output: {PRED_FILE}'

    pred_rows = read_rows(PRED_FILE)
    exp_rows = read_rows(EXPECTED_FILE)

    assert len(pred_rows) == 23, f'expected 23 data rows, got {len(pred_rows)}'
    assert pred_rows == exp_rows, 'minute cards do not match expected content'

    for i, row in enumerate(pred_rows):
        minute = int(row['minute'])
        second_mark = int(row['second_mark'])
        assert minute == i, f'minute index mismatch at row {i}'
        assert second_mark == minute * 60, f'second_mark mismatch at minute {minute}'
        assert row['chapter_title'], f'empty chapter_title at minute {minute}'


if __name__ == '__main__':
    main()
