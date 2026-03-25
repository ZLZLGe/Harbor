import csv
import json
import subprocess
from pathlib import Path

SOURCE = Path('/root/transfer2_source.mp4')
CHAPTERS = Path('/root/data/transfer2_chapters.json')
CLIPS_DIR = Path('/root/transfer2_clips')
MANIFEST = Path('/root/transfer2_sampler_manifest.csv')
REEL = Path('/root/transfer2_sampler_reel.mp4')
CLIP_LENGTH = 2.4


def ffprobe_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', str(path),
        ],
        text=True,
    ).strip()
    return float(out)


def expected_rows() -> list[dict[str, str]]:
    duration = ffprobe_duration(SOURCE)
    chapters = json.loads(CHAPTERS.read_text(encoding='utf-8'))
    rows = []
    for idx, chapter in enumerate(chapters, start=1):
        start = float(chapter['start'])
        if start >= duration:
            continue
        end = min(start + CLIP_LENGTH, duration)
        if end <= start:
            continue
        rows.append(
            {
                'clip_name': f'clip_{idx:02d}_{chapter["chapter_id"]}.mp4',
                'chapter_id': str(chapter['chapter_id']),
                'topic': str(chapter['topic']),
                'start': f'{start:.3f}',
                'end': f'{end:.3f}',
                'clip_duration': f'{(end - start):.3f}',
            }
        )
    return rows


def main() -> None:
    assert MANIFEST.exists(), 'missing /root/transfer2_sampler_manifest.csv'
    assert REEL.exists(), 'missing /root/transfer2_sampler_reel.mp4'
    assert CLIPS_DIR.exists(), 'missing /root/transfer2_clips directory'

    with MANIFEST.open('r', encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle)
        observed_rows = list(reader)

    expected = expected_rows()
    assert observed_rows == expected, 'sampler manifest CSV mismatch'
    assert len(observed_rows) > 0, 'manifest should contain at least one clip row'

    total_duration = 0.0
    for row in observed_rows:
        clip_path = CLIPS_DIR / row['clip_name']
        assert clip_path.exists(), f'missing clip file: {clip_path}'
        clip_duration = ffprobe_duration(clip_path)
        expected_clip_duration = float(row['clip_duration'])
        assert abs(clip_duration - expected_clip_duration) <= 0.85, (
            f'clip duration mismatch for {row["clip_name"]}: '
            f'expected about {expected_clip_duration:.3f}, got {clip_duration:.3f}'
        )
        total_duration += expected_clip_duration

    reel_duration = ffprobe_duration(REEL)
    assert reel_duration > 0.5, 'sampler reel too short'
    assert abs(reel_duration - total_duration) <= 1.35, (
        f'reel duration mismatch: expected about {total_duration:.3f}, got {reel_duration:.3f}'
    )


if __name__ == '__main__':
    main()
