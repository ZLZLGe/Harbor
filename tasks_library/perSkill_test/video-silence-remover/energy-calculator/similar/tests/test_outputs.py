import json
from pathlib import Path

OUT = Path('/root/similar_energy_profile.json')


def approx(a: float, b: float, eps: float = 1e-6) -> bool:
    return abs(float(a) - float(b)) <= eps


def main() -> None:
    assert OUT.exists(), f'missing output file: {OUT}'
    report = json.loads(OUT.read_text(encoding='utf-8'))

    assert report['track_id'] == 'lesson-track-a'
    assert report['window_seconds'] == 1

    expected_energies = [0.0, 120.0, 240.0, 0.0, 360.0]
    assert len(report['energies']) == len(expected_energies)
    for got, exp in zip(report['energies'], expected_energies):
        assert approx(got, exp), f'energy mismatch: {got} vs {exp}'

    stats = report['stats']
    assert approx(stats['min'], 0.0)
    assert approx(stats['max'], 360.0)
    assert approx(stats['mean'], 144.0)
    assert approx(stats['std'], 139.9428454762872, eps=1e-5)

    assert report['quiet_seconds'] == [0, 3]
    assert report['loudest_second'] == 4


if __name__ == '__main__':
    main()
