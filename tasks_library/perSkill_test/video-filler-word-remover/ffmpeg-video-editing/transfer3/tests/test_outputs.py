import json
import subprocess
from pathlib import Path

SOURCE = Path('/root/transfer3_source.mp4')
WINDOWS = Path('/root/data/transfer3_windows.json')
OUT_DIR = Path('/root/transfer3_window_pack')
INDEX = Path('/root/transfer3_window_index.json')


def ffprobe_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', str(path),
        ],
        text=True,
    ).strip()
    return float(out)


def expected_index() -> dict:
    duration = ffprobe_duration(SOURCE)
    windows = json.loads(WINDOWS.read_text(encoding='utf-8'))

    normalized = []
    for row in windows:
        start = max(0.0, float(row['start']))
        end = min(duration, float(row['end']))
        if end <= start:
            continue
        normalized.append(
            {
                'window_id': str(row['window_id']),
                'purpose': str(row['purpose']),
                'start': round(start, 3),
                'end': round(end, 3),
                'duration': round(end - start, 3),
                'output_file': f"{row['window_id']}.mp4",
            }
        )

    return {
        'source_video': 'transfer3_source.mp4',
        'output_dir': 'transfer3_window_pack',
        'windows': normalized,
        'total_windows': len(normalized),
        'total_duration_seconds': round(sum(item['duration'] for item in normalized), 3),
    }


def main() -> None:
    assert OUT_DIR.exists(), 'missing /root/transfer3_window_pack'
    assert INDEX.exists(), 'missing /root/transfer3_window_index.json'

    observed = json.loads(INDEX.read_text(encoding='utf-8'))
    expected = expected_index()

    assert observed == expected, 'window index JSON mismatch'
    assert observed['total_windows'] > 0, 'window index should include at least one clip'

    for row in observed['windows']:
        clip_path = OUT_DIR / row['output_file']
        assert clip_path.exists(), f'missing clip file: {clip_path}'
        actual_duration = ffprobe_duration(clip_path)
        assert abs(actual_duration - float(row['duration'])) <= 0.85, (
            f'duration mismatch for {row["output_file"]}: '
            f'expected about {row["duration"]:.3f}, got {actual_duration:.3f}'
        )


if __name__ == '__main__':
    main()
