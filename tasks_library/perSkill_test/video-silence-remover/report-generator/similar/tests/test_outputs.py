import json
import subprocess
from pathlib import Path

OUT = Path('/root/similar_compression_report.json')
ORIG = Path('/root/data/source_session.mp4')
COMP = Path('/root/data/trimmed_session.mp4')
SEGS = Path('/root/data/segments_removed.json')


def ffprobe_duration(path: Path) -> float:
    proc = subprocess.run(
        [
            'ffprobe',
            '-v',
            'error',
            '-show_entries',
            'format=duration',
            '-of',
            'default=noprint_wrappers=1:nokey=1',
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(proc.stdout.strip())


def approx(a: float, b: float, eps: float = 0.06) -> bool:
    return abs(a - b) <= eps


def main() -> None:
    assert OUT.exists(), f'missing output file: {OUT}'

    report = json.loads(OUT.read_text(encoding='utf-8'))
    expected_segments = json.loads(SEGS.read_text(encoding='utf-8'))['segments']

    required = {
        'original_duration_seconds',
        'compressed_duration_seconds',
        'removed_duration_seconds',
        'compression_percentage',
        'segments_removed',
    }
    assert required.issubset(report.keys()), f'missing fields: {required - set(report.keys())}'

    orig = ffprobe_duration(ORIG)
    comp = ffprobe_duration(COMP)
    removed = orig - comp
    pct = (removed / orig) * 100

    assert approx(float(report['original_duration_seconds']), round(orig, 2))
    assert approx(float(report['compressed_duration_seconds']), round(comp, 2))
    assert approx(float(report['removed_duration_seconds']), round(removed, 2))
    assert approx(float(report['compression_percentage']), round(pct, 2), eps=0.1)

    assert report['segments_removed'] == expected_segments


if __name__ == '__main__':
    main()
