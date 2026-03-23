import json
from pathlib import Path

OUT = Path('/root/intro_trim_plan.json')
EXP = Path('/tests/expected_trim_plan.json')


def main() -> None:
    assert OUT.exists(), f'missing output: {OUT}'

    out = json.loads(OUT.read_text(encoding='utf-8'))
    exp = json.loads(EXP.read_text(encoding='utf-8'))

    assert out == exp

    detected = out['detected_intro_end_seconds']
    buffer_s = out['policy_applied']['safety_buffer_seconds']
    min_s = out['policy_applied']['min_publish_start_second']
    max_s = out['policy_applied']['max_publish_start_second']

    recomputed = min(max(detected + buffer_s, min_s), max_s)
    assert out['publish_start_seconds'] == recomputed
    assert out['cut_segment']['start'] == 0
    assert out['cut_segment']['end'] == out['publish_start_seconds']
    assert out['cut_segment']['duration'] == out['cut_segment']['end'] - out['cut_segment']['start']


if __name__ == '__main__':
    main()
