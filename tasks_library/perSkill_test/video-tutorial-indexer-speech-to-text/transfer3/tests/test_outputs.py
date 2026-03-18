import json
from pathlib import Path

PRED_FILE = Path('/root/chapter_duration_leaderboard.json')
EXPECTED_FILE = Path(__file__).parent / 'expected_duration_leaderboard.json'


def main() -> None:
    assert PRED_FILE.exists(), f'missing output: {PRED_FILE}'
    pred = json.loads(PRED_FILE.read_text())
    expected = json.loads(EXPECTED_FILE.read_text())

    assert pred['video_info'] == expected['video_info']

    rows = pred['top_longest_chapters']
    exp_rows = expected['top_longest_chapters']
    assert len(rows) == 10, f'expected 10 rows, got {len(rows)}'
    assert rows == exp_rows, 'leaderboard content mismatch'

    for i, row in enumerate(rows, start=1):
        assert row['rank'] == i, f'rank mismatch at position {i}'
        assert row['duration_seconds'] == row['end_time'] - row['start_time']

    durations = [row['duration_seconds'] for row in rows]
    assert durations == sorted(durations, reverse=True), 'durations not sorted desc'


if __name__ == '__main__':
    main()
