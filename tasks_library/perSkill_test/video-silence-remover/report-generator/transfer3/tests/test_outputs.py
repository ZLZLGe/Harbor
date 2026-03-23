import json
import subprocess
from pathlib import Path

OUT = Path('/root/transfer3_candidate_selection.json')
MANIFEST = Path('/root/data/candidate_manifest.json')


def ffprobe_duration(path: str) -> float:
    proc = subprocess.run(
        [
            'ffprobe',
            '-v',
            'error',
            '-show_entries',
            'format=duration',
            '-of',
            'default=noprint_wrappers=1:nokey=1',
            path,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(proc.stdout.strip())


def approx(a: float, b: float, eps: float = 0.1) -> bool:
    return abs(a - b) <= eps


def main() -> None:
    assert OUT.exists(), f'missing output: {OUT}'

    out = json.loads(OUT.read_text(encoding='utf-8'))
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    window = manifest['target_window']

    assert out['target_window'] == window
    assert len(out['candidates']) == len(manifest['candidates'])

    original = '/root/data/master_source.mp4'
    orig_duration = ffprobe_duration(original)

    in_window = []
    for item, spec in zip(out['candidates'], manifest['candidates']):
        assert item['candidate_id'] == spec['candidate_id']
        report = item['report']

        comp = ffprobe_duration(spec['compressed'])
        removed = orig_duration - comp
        pct = (removed / orig_duration) * 100

        assert approx(float(report['original_duration_seconds']), round(orig_duration, 2))
        assert approx(float(report['compressed_duration_seconds']), round(comp, 2))
        assert approx(float(report['removed_duration_seconds']), round(removed, 2))
        assert approx(float(report['compression_percentage']), round(pct, 2), eps=0.12)

        expected_segments = json.loads(Path(spec['segments']).read_text(encoding='utf-8'))['segments']
        assert report['segments_removed'] == expected_segments

        if float(window['min_pct']) <= float(report['compression_percentage']) <= float(window['max_pct']):
            in_window.append(item)

    assert in_window, 'at least one candidate should be within window'

    expected = min(
        in_window,
        key=lambda c: (abs(float(c['report']['compression_percentage']) - float(window['target_pct'])), c['candidate_id']),
    )

    assert out['selected_candidate'] == expected['candidate_id']
    assert out['selected_report'] == expected['report']


if __name__ == '__main__':
    main()
