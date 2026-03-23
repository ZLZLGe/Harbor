import json
from pathlib import Path

PRED_FILE = Path('/root/tutorial_phase_timeline.json')
EXPECTED_FILE = Path(__file__).parent / 'expected_phase_timeline.json'


def main() -> None:
    assert PRED_FILE.exists(), f'missing output: {PRED_FILE}'
    pred = json.loads(PRED_FILE.read_text())
    expected = json.loads(EXPECTED_FILE.read_text())

    assert set(pred.keys()) == {'video_info', 'phases'}
    assert pred['video_info'] == expected['video_info']

    phases = pred['phases']
    exp_phases = expected['phases']
    assert len(phases) == 8, f'expected 8 phases, got {len(phases)}'

    prev_end = -1
    for i, (phase, exp_phase) in enumerate(zip(phases, exp_phases), start=1):
        assert phase['phase_id'] == f'phase_{i}'
        assert phase['phase_title'] == exp_phase['phase_title']
        assert phase['chapter_span'] == exp_phase['chapter_span']
        assert isinstance(phase['start_time'], (int, float))
        assert isinstance(phase['end_time'], (int, float))
        assert phase['start_time'] < phase['end_time']
        assert phase['start_time'] >= 0
        assert phase['end_time'] <= 1382
        assert phase['start_time'] >= prev_end
        prev_end = phase['end_time']
        assert phase['start_time'] == exp_phase['start_time']
        assert phase['end_time'] == exp_phase['end_time']


if __name__ == '__main__':
    main()
