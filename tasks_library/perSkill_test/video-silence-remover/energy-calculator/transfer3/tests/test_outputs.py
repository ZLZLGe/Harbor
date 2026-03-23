import json
from pathlib import Path

OUT = Path('/root/transfer3_energy_delta.json')


def approx(a: float, b: float, eps: float = 1e-6) -> bool:
    return abs(float(a) - float(b)) <= eps


def main() -> None:
    assert OUT.exists(), f'missing output file: {OUT}'
    report = json.loads(OUT.read_text(encoding='utf-8'))

    assert report['comparison_id'] == 'line-a-vs-line-b'
    assert report['window_seconds'] == 1

    assert approx(report['baseline_mean'], 123.33333333333333)
    assert approx(report['candidate_mean'], 101.66666666666667)
    assert approx(report['reduction_ratio'], 0.17567567567567566)

    expected_delta = [10.0, 20.0, 40.0, 30.0, 20.0, 10.0]
    assert len(report['per_second_delta']) == len(expected_delta)
    for got, exp in zip(report['per_second_delta'], expected_delta):
        assert approx(got, exp), f'delta mismatch: {got} vs {exp}'

    assert report['improved_seconds'] == [0, 1, 2, 3, 4, 5]


if __name__ == '__main__':
    main()
