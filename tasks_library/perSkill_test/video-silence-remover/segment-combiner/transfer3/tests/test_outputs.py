import csv
from pathlib import Path

OUT = Path('/root/transfer3_trim_budget_report.csv')
EXP = Path('/tests/expected_transfer3_trim_budget_report.csv')


def load_csv(path: Path):
    with path.open('r', encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def main() -> None:
    assert OUT.exists(), f'missing output: {OUT}'

    out_rows = load_csv(OUT)
    exp_rows = load_csv(EXP)

    assert out_rows == exp_rows, 'trim budget report mismatch'

    ranks = [int(row['rank']) for row in out_rows]
    assert ranks == [1, 2, 3]


if __name__ == '__main__':
    main()
