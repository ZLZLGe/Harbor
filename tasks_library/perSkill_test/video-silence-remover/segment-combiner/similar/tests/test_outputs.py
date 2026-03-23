import json
from pathlib import Path

OUT = Path('/root/similar_combined_segments.json')
EXP = Path('/tests/expected_similar_combined_segments.json')


def main() -> None:
    assert OUT.exists(), f'missing output: {OUT}'
    out = json.loads(OUT.read_text(encoding='utf-8'))
    exp = json.loads(EXP.read_text(encoding='utf-8'))

    assert out == exp, f'combined output mismatch: {out}'

    segments = out['segments']
    starts = [seg['start'] for seg in segments]
    assert starts == sorted(starts), 'segments are not sorted by start'
    assert out['total_segments'] == len(segments)
    assert out['total_duration_seconds'] == sum(seg['duration'] for seg in segments)


if __name__ == '__main__':
    main()
