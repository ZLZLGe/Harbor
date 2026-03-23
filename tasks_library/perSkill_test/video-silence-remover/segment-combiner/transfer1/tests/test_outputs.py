import json
from pathlib import Path

OUT_COMBINED = Path('/root/transfer1_all_segments.json')
OUT_MANIFEST = Path('/root/transfer1_review_manifest.json')
EXP_COMBINED = Path('/tests/expected_transfer1_all_segments.json')
EXP_MANIFEST = Path('/tests/expected_transfer1_review_manifest.json')


def main() -> None:
    assert OUT_COMBINED.exists(), f'missing output: {OUT_COMBINED}'
    assert OUT_MANIFEST.exists(), f'missing output: {OUT_MANIFEST}'

    out_combined = json.loads(OUT_COMBINED.read_text(encoding='utf-8'))
    out_manifest = json.loads(OUT_MANIFEST.read_text(encoding='utf-8'))
    exp_combined = json.loads(EXP_COMBINED.read_text(encoding='utf-8'))
    exp_manifest = json.loads(EXP_MANIFEST.read_text(encoding='utf-8'))

    assert out_combined == exp_combined, 'combined segment timeline mismatch'
    assert out_manifest == exp_manifest, 'audit manifest mismatch'

    assert out_manifest['total_segments'] == len(out_combined['segments'])
    assert out_manifest['total_duration_seconds'] == sum(seg['duration'] for seg in out_combined['segments'])


if __name__ == '__main__':
    main()
