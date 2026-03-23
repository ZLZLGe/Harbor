import json
import subprocess
from pathlib import Path

SOURCE = Path('/root/similar_source.mp4')
WINDOWS = Path('/root/data/similar_filler_windows.json')
OUTPUT_VIDEO = Path('/root/similar_filler_montage.mp4')
REPORT = Path('/root/similar_filler_windows_report.json')


def ffprobe_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', str(path),
        ],
        text=True,
    ).strip()
    return float(out)


def ffprobe_stream_types(path: Path) -> set[str]:
    out = subprocess.check_output(
        [
            'ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type',
            '-of', 'default=noprint_wrappers=1:nokey=1', str(path),
        ],
        text=True,
    )
    return {line.strip() for line in out.splitlines() if line.strip()}


def main() -> None:
    assert SOURCE.exists(), 'missing /root/similar_source.mp4'
    assert WINDOWS.exists(), 'missing /root/data/similar_filler_windows.json'
    assert OUTPUT_VIDEO.exists(), 'missing /root/similar_filler_montage.mp4'
    assert REPORT.exists(), 'missing /root/similar_filler_windows_report.json'

    windows = json.loads(WINDOWS.read_text(encoding='utf-8'))
    windows = sorted(windows, key=lambda item: float(item['start']))
    report = json.loads(REPORT.read_text(encoding='utf-8'))

    expected_total = sum(float(item['end']) - float(item['start']) for item in windows)

    assert report['source_video'] == 'similar_source.mp4'
    assert report['output_video'] == 'similar_filler_montage.mp4'
    assert report['segments_used'] == windows
    assert int(report['total_segments']) == len(windows)
    assert abs(float(report['total_duration_seconds']) - expected_total) < 1e-6

    output_duration = ffprobe_duration(OUTPUT_VIDEO)
    assert output_duration > 0.5, 'output montage too short'
    assert abs(output_duration - expected_total) <= 1.25, (
        f'output duration mismatch: expected about {expected_total:.3f}, got {output_duration:.3f}'
    )

    stream_types = ffprobe_stream_types(OUTPUT_VIDEO)
    assert 'video' in stream_types, 'output must contain video stream'
    assert 'audio' in stream_types, 'output must contain audio stream'


if __name__ == '__main__':
    main()
