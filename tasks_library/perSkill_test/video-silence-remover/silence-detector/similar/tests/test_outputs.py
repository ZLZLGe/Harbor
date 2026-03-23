import json
from pathlib import Path

OUT = Path('/root/initial_silence_report.json')
EXP = Path('/tests/expected_report.json')


def approx(a: float, b: float, eps: float = 1e-6) -> bool:
    return abs(a - b) <= eps


def main() -> None:
    assert OUT.exists(), f'missing output: {OUT}'

    out = json.loads(OUT.read_text(encoding='utf-8'))
    exp = json.loads(EXP.read_text(encoding='utf-8'))

    assert out['method'] == exp['method']
    assert out['segments'] == exp['segments']
    assert out['total_segments'] == exp['total_segments']
    assert out['total_duration_seconds'] == exp['total_duration_seconds']
    assert out['parameters'] == exp['parameters']

    assert approx(float(out['analysis']['initial_avg']), float(exp['analysis']['initial_avg']))
    assert approx(float(out['analysis']['threshold']), float(exp['analysis']['threshold']))

    assert out['total_segments'] == len(out['segments'])


if __name__ == '__main__':
    main()
