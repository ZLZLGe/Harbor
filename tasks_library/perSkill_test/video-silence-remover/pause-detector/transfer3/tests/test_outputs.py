import json
import subprocess
from pathlib import Path

OUT = Path('/root/transfer3_overlap_windows.json')
NARRATION = Path('/root/data/transfer3_narration_track.json')
SCREEN = Path('/root/data/transfer3_screen_track.json')


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


def detect(input_path: Path, ratio: str, tmp_path: Path) -> list[dict]:
    subprocess.run(
        [
            'python3',
            find_skill_script(),
            '--energies',
            str(input_path),
            '--start-time',
            '0',
            '--threshold-ratio',
            ratio,
            '--min-duration',
            '2',
            '--window-size',
            '5',
            '--output',
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(tmp_path.read_text(encoding='utf-8'))['segments']


def intersect(a: list[dict], b: list[dict]) -> list[dict]:
    out = []
    i = 0
    j = 0
    while i < len(a) and j < len(b):
        seg_a = a[i]
        seg_b = b[j]
        start = max(seg_a['start'], seg_b['start'])
        end = min(seg_a['end'], seg_b['end'])
        if start < end:
            out.append({'start': start, 'end': end, 'duration': end - start})
        if seg_a['end'] <= seg_b['end']:
            i += 1
        else:
            j += 1
    return out


def main() -> None:
    assert OUT.exists(), f'missing output file: {OUT}'

    narration = detect(NARRATION, '0.56', Path('/tmp/transfer3_expected_narration.json'))
    screen = detect(SCREEN, '0.60', Path('/tmp/transfer3_expected_screen.json'))
    overlap = intersect(narration, screen)

    expected = {
        'narration_segments': narration,
        'screen_segments': screen,
        'overlap_segments': overlap,
        'overlap_duration_seconds': sum(seg['duration'] for seg in overlap),
        'joint_pause_count': len(overlap),
    }

    out = json.loads(OUT.read_text(encoding='utf-8'))
    assert out == expected, 'overlap report JSON mismatch'


if __name__ == '__main__':
    main()
