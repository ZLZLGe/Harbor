import json
import subprocess
from pathlib import Path

OUT = Path('/root/transfer1_editorial_pause_audit.json')
INPUT = Path('/root/data/transfer1_board_session_energies.json')


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


def build_expected() -> dict:
    expected_path = Path('/tmp/transfer1_expected_raw.json')
    subprocess.run(
        [
            'python3',
            find_skill_script(),
            '--energies',
            str(INPUT),
            '--start-time',
            '2',
            '--threshold-ratio',
            '0.6',
            '--min-duration',
            '2',
            '--window-size',
            '7',
            '--output',
            str(expected_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    raw = json.loads(expected_path.read_text(encoding='utf-8'))
    source = json.loads(INPUT.read_text(encoding='utf-8'))
    segments = raw['segments']

    total = sum(seg['duration'] for seg in segments)
    longest = max([seg['duration'] for seg in segments], default=0)
    top_two = sorted(segments, key=lambda s: (-s['duration'], s['start']))[:2]

    return {
        'session_id': source['session_id'],
        'parameters': {
            'start_time': 2,
            'threshold_ratio': 0.6,
            'min_duration': 2,
            'window_size': 7,
        },
        'pause_segments': segments,
        'total_pause_seconds': total,
        'longest_pause_seconds': longest,
        'top_two_segments': top_two,
        'qa_flag': 'needs-review' if longest >= 4 else 'ok',
    }


def main() -> None:
    assert OUT.exists(), f'missing output file: {OUT}'
    out = json.loads(OUT.read_text(encoding='utf-8'))
    expected = build_expected()

    assert out == expected, 'editorial pause audit JSON mismatch'

    assert out['total_pause_seconds'] == sum(seg['duration'] for seg in out['pause_segments'])
    assert out['longest_pause_seconds'] == max([seg['duration'] for seg in out['pause_segments']], default=0)


if __name__ == '__main__':
    main()
