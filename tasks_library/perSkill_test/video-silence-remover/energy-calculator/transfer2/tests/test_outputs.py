import json
from pathlib import Path

OUT = Path('/root/transfer2_quiet_intervals.json')


def approx(a: float, b: float, eps: float = 1e-6) -> bool:
    return abs(float(a) - float(b)) <= eps


def main() -> None:
    assert OUT.exists(), f'missing output file: {OUT}'
    report = json.loads(OUT.read_text(encoding='utf-8'))

    assert report['recording_id'] == 'night-watch-3'
    assert report['quiet_threshold'] == 15
    assert approx(report['window_seconds'], 1.0)

    expected = [12.0, 10.0, 9.0, 80.0, 85.0, 8.0, 7.0]
    assert len(report['energies']) == len(expected)
    for got, exp in zip(report['energies'], expected):
        assert approx(got, exp), f'energy mismatch: {got} vs {exp}'

    assert report['quiet_intervals'] == [
        {'start': 0, 'end': 3, 'duration': 3},
        {'start': 5, 'end': 7, 'duration': 2},
    ]
    assert report['total_quiet_seconds'] == 5


if __name__ == '__main__':
    main()
