import json
import subprocess
from pathlib import Path

OUT = Path('/root/transfer2_batch_summary.json')
MANIFEST = Path('/root/data/batch_manifest.json')


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

    assert out['batch_id'] == manifest['batch_id']
    assert len(out['reports']) == len(manifest['jobs'])

    for item, job in zip(out['reports'], manifest['jobs']):
        assert item['clip_id'] == job['clip_id']
        report = item['report']

        orig = ffprobe_duration(job['original'])
        comp = ffprobe_duration(job['compressed'])
        removed = orig - comp
        pct = (removed / orig) * 100

        assert approx(float(report['original_duration_seconds']), round(orig, 2))
        assert approx(float(report['compressed_duration_seconds']), round(comp, 2))
        assert approx(float(report['removed_duration_seconds']), round(removed, 2))
        assert approx(float(report['compression_percentage']), round(pct, 2), eps=0.12)

        if 'segments' in job:
            expected = json.loads(Path(job['segments']).read_text(encoding='utf-8'))['segments']
            assert report['segments_removed'] == expected
        else:
            assert report['segments_removed'] == []

    portfolio = out['portfolio']
    total_original = sum(float(x['report']['original_duration_seconds']) for x in out['reports'])
    total_compressed = sum(float(x['report']['compressed_duration_seconds']) for x in out['reports'])
    total_removed = sum(float(x['report']['removed_duration_seconds']) for x in out['reports'])
    mean_pct = sum(float(x['report']['compression_percentage']) for x in out['reports']) / len(out['reports'])

    assert approx(float(portfolio['total_original_seconds']), round(total_original, 2))
    assert approx(float(portfolio['total_compressed_seconds']), round(total_compressed, 2))
    assert approx(float(portfolio['total_removed_seconds']), round(total_removed, 2))
    assert approx(float(portfolio['mean_compression_percentage']), round(mean_pct, 2), eps=0.12)


if __name__ == '__main__':
    main()
