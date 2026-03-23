import json
from pathlib import Path

OUT = Path('/root/transfer1_energy_alerts.json')


def approx(a: float, b: float, eps: float = 1e-6) -> bool:
    return abs(float(a) - float(b)) <= eps


def main() -> None:
    assert OUT.exists(), f'missing output file: {OUT}'
    report = json.loads(OUT.read_text(encoding='utf-8'))

    assert report['clip_id'] == 'broadcast-17'
    assert approx(report['window_seconds'], 0.5)

    expected = [20.0, 60.0, 140.0, 300.0, 300.0, 140.0, 60.0, 20.0]
    assert len(report['energies']) == len(expected)
    for got, exp in zip(report['energies'], expected):
        assert approx(got, exp), f'energy mismatch: {got} vs {exp}'

    assert report['peak_windows'] == [3, 4]
    assert report['alert_windows'] == [2, 3, 4, 5]
    assert approx(report['mean_energy'], 130.0)


if __name__ == '__main__':
    main()
