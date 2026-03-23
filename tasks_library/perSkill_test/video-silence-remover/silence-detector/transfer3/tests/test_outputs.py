import json
from pathlib import Path

OUT = Path('/root/silence_qc_flags.json')
EXP = Path('/tests/expected_silence_qc_flags.json')


def main() -> None:
    assert OUT.exists(), f'missing output: {OUT}'

    out = json.loads(OUT.read_text(encoding='utf-8'))
    exp = json.loads(EXP.read_text(encoding='utf-8'))

    assert out == exp

    counts = {'ok': 0, 'review': 0, 'reject': 0}
    for row in out['records']:
        counts[row['qc_flag']] += 1

    assert counts['ok'] == out['summary']['ok']
    assert counts['review'] == out['summary']['review']
    assert counts['reject'] == out['summary']['reject']
    assert len(out['records']) == out['summary']['total']


if __name__ == '__main__':
    main()
