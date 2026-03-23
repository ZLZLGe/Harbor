import json
import subprocess
from pathlib import Path

OUT = Path('/root/transfer1_governance_report.json')
ORIG = Path('/root/data/original_briefing.mp4')
COMP = Path('/root/data/trimmed_briefing.mp4')
POL = Path('/root/data/governance_policy.json')


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


def approx(a: float, b: float, eps: float = 0.08) -> bool:
    return abs(a - b) <= eps


def main() -> None:
    assert OUT.exists(), f'missing output: {OUT}'

    out = json.loads(OUT.read_text(encoding='utf-8'))
    pol = json.loads(POL.read_text(encoding='utf-8'))

    assert out['report_id'] == pol['report_id']
    assert out['source_asset'] == pol['source_asset']

    report = out['compression_report']
    assert report['segments_removed'] == []

    orig = ffprobe_duration(ORIG)
    comp = ffprobe_duration(COMP)
    removed = orig - comp
    pct = (removed / orig) * 100

    assert approx(float(report['original_duration_seconds']), round(orig, 2))
    assert approx(float(report['compressed_duration_seconds']), round(comp, 2))
    assert approx(float(report['removed_duration_seconds']), round(removed, 2))
    assert approx(float(report['compression_percentage']), round(pct, 2), eps=0.12)

    gate = out['quality_gate']
    minimum = float(pol['minimum_removed_seconds'])
    assert float(gate['minimum_removed_seconds']) == minimum
    assert gate['passed'] == (float(report['removed_duration_seconds']) >= minimum)


if __name__ == '__main__':
    main()
