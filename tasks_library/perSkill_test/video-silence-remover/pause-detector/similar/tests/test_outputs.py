import json
import subprocess
from pathlib import Path

OUT = Path('/root/similar_pause_segments.json')
INPUT = Path('/root/data/similar_lecture_energies.json')


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


def main() -> None:
    assert OUT.exists(), f'missing output file: {OUT}'

    expected_path = Path('/tmp/similar_expected.json')
    subprocess.run(
        [
            'python3',
            find_skill_script(),
            '--energies',
            str(INPUT),
            '--start-time',
            '5',
            '--threshold-ratio',
            '0.55',
            '--min-duration',
            '2',
            '--window-size',
            '5',
            '--output',
            str(expected_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    out = json.loads(OUT.read_text(encoding='utf-8'))
    expected = json.loads(expected_path.read_text(encoding='utf-8'))

    assert out == expected, 'output JSON does not match expected detector result'

    segments = out['segments']
    starts = [seg['start'] for seg in segments]
    assert starts == sorted(starts), 'segments are not sorted by start'
    assert out['total_segments'] == len(segments), 'total_segments mismatch'
    assert out['total_duration_seconds'] == sum(seg['duration'] for seg in segments), 'total_duration_seconds mismatch'


if __name__ == '__main__':
    main()
