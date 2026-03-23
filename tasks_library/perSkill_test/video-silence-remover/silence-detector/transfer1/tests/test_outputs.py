import csv
from pathlib import Path

OUT = Path('/root/pre_roll_leaderboard.csv')
EXP = Path('/tests/expected_pre_roll_leaderboard.csv')


def load_csv(path: Path):
    with path.open('r', encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def main() -> None:
    assert OUT.exists(), f'missing output: {OUT}'

    out_rows = load_csv(OUT)
    exp_rows = load_csv(EXP)

    assert out_rows == exp_rows, f'leaderboard mismatch: {out_rows}'

    assert [int(r['rank']) for r in out_rows] == [1, 2, 3]
    silences = [int(r['silence_seconds']) for r in out_rows]
    assert silences == sorted(silences, reverse=True)


if __name__ == '__main__':
    main()
