import json
import subprocess
from pathlib import Path

SOURCE = Path('/root/transfer1_source.mp4')
REMOVE = Path('/root/data/transfer1_remove_windows.json')
OUT_VIDEO = Path('/root/transfer1_clean_cut.mp4')
REPORT = Path('/root/transfer1_redaction_report.json')


def ffprobe_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', str(path),
        ],
        text=True,
    ).strip()
    return float(out)


def merge_windows(rows: list[dict], duration: float) -> list[tuple[float, float]]:
    clipped = []
    for row in rows:
        start = max(0.0, float(row['start']))
        end = min(duration, float(row['end']))
        if end > start:
            clipped.append((start, end))
    clipped.sort()

    merged: list[tuple[float, float]] = []
    for start, end in clipped:
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    return merged


def expected_report() -> dict:
    duration = ffprobe_duration(SOURCE)
    raw = json.loads(REMOVE.read_text(encoding='utf-8'))
    removed = merge_windows(raw, duration)

    keep = []
    cursor = 0.0
    for start, end in removed:
        if start > cursor:
            keep.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < duration:
        keep.append((cursor, duration))

    removed_total = sum(b - a for a, b in removed)
    kept_total = sum(b - a for a, b in keep)

    return {
        'source_video': 'transfer1_source.mp4',
        'output_video': 'transfer1_clean_cut.mp4',
        'source_duration_seconds': round(duration, 3),
        'removed_windows_merged': [{'start': round(a, 3), 'end': round(b, 3)} for a, b in removed],
        'keep_windows': [{'start': round(a, 3), 'end': round(b, 3)} for a, b in keep],
        'removed_total_seconds': round(removed_total, 3),
        'kept_total_seconds': round(kept_total, 3),
    }


def main() -> None:
    assert OUT_VIDEO.exists(), 'missing /root/transfer1_clean_cut.mp4'
    assert REPORT.exists(), 'missing /root/transfer1_redaction_report.json'

    observed = json.loads(REPORT.read_text(encoding='utf-8'))
    expected = expected_report()

    assert observed == expected, 'redaction report mismatch'

    out_duration = ffprobe_duration(OUT_VIDEO)
    assert out_duration > 0.5, 'clean cut output too short'
    assert abs(out_duration - expected['kept_total_seconds']) <= 1.25, (
        f'output duration mismatch: expected about {expected["kept_total_seconds"]:.3f}, got {out_duration:.3f}'
    )


if __name__ == '__main__':
    main()
