import csv
import json
import subprocess
from pathlib import Path

OUT = Path('/root/transfer2_pause_break_index.csv')
INPUTS = [
    Path('/root/data/transfer2_room_a.json'),
    Path('/root/data/transfer2_room_b.json'),
    Path('/root/data/transfer2_room_c.json'),
]


def find_skill_script() -> str:
    bases = [
        '/root/.codex/skills',
        '/root/.claude/skills',
        '/root/.opencode/skill',
        '/root/.goose/skills',
        '/root/.factory/skills',
        '/root/.agents/skills',
        '/root/skills',
        '/root/.gemini/skills',
    ]
    for base in bases:
        candidate = Path(base) / 'pause-detector' / 'scripts' / 'detect_pauses.py'
        if candidate.exists():
            return str(candidate)
    raise AssertionError('pause-detector skill script not found')


def build_expected_rows() -> list[list[str]]:
    rows = []
    script = find_skill_script()
    for src in INPUTS:
        raw_out = Path(f'/tmp/{src.stem}_expected.json')
        subprocess.run(
            [
                'python3',
                script,
                '--energies',
                str(src),
                '--start-time',
                '1',
                '--threshold-ratio',
                '0.58',
                '--min-duration',
                '2',
                '--window-size',
                '5',
                '--output',
                str(raw_out),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        source = json.loads(src.read_text(encoding='utf-8'))
        segments = json.loads(raw_out.read_text(encoding='utf-8'))['segments']
        count = len(segments)
        first_start = segments[0]['start'] if segments else -1
        total = sum(seg['duration'] for seg in segments)
        longest = max([seg['duration'] for seg in segments], default=0)
        rows.append([
            source['session_id'],
            str(count),
            str(first_start),
            str(total),
            str(longest),
        ])
    rows.sort(key=lambda row: row[0])
    return rows


def main() -> None:
    assert OUT.exists(), f'missing output file: {OUT}'

    with OUT.open('r', encoding='utf-8', newline='') as f:
        reader = list(csv.reader(f))

    assert reader, 'CSV output is empty'
    header = reader[0]
    expected_header = [
        'session_id',
        'detected_break_count',
        'first_break_start',
        'total_pause_seconds',
        'longest_pause_seconds',
    ]
    assert header == expected_header, f'CSV header mismatch: {header}'

    rows = reader[1:]
    expected_rows = build_expected_rows()

    assert rows == expected_rows, f'CSV rows mismatch: {rows} != {expected_rows}'


if __name__ == '__main__':
    main()
