import json
from pathlib import Path

OUT = Path('/root/transfer2_overlap_alerts.json')
EXP = Path('/tests/expected_transfer2_overlap_alerts.json')


def main() -> None:
    assert OUT.exists(), f'missing output: {OUT}'
    out = json.loads(OUT.read_text(encoding='utf-8'))
    exp = json.loads(EXP.read_text(encoding='utf-8'))

    assert out == exp, 'overlap alert output mismatch'

    for alert in out['overlap_alerts']:
        ov = alert['overlap']
        assert ov['duration'] == ov['end'] - ov['start']

    for seg in out['non_overlapping_segments']:
        assert seg['duration'] == seg['end'] - seg['start']


if __name__ == '__main__':
    main()
