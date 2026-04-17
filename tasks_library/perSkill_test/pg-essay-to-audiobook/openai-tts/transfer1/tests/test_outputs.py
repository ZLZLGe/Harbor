import json
import subprocess
from pathlib import Path

CONFIG = json.loads(Path('/root/data/task_config.json').read_text())
SOURCE = json.loads(Path('/root/data/incident_updates.json').read_text())


def probe_duration(path: str) -> float:
    cmd = [
        'ffprobe',
        '-v',
        'error',
        '-show_entries',
        'format=duration',
        '-of',
        'default=noprint_wrappers=1:nokey=1',
        path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def test_outputs_exist():
    assert Path(CONFIG['output_audio']).exists()
    assert Path(CONFIG['output_cues']).exists()


def test_cues_schema_and_order():
    cues = json.loads(Path(CONFIG['output_cues']).read_text())
    assert cues['voice'] == CONFIG['voice']
    assert cues['model'] == CONFIG['model']
    segments = cues['segments']
    assert len(segments) == len(SOURCE['updates'])

    expected_codes = [x['update_code'] for x in SOURCE['updates']]
    actual_codes = [x['update_code'] for x in segments]
    assert actual_codes == expected_codes

    prev_end = -1.0
    for seg in segments:
        assert seg['start_sec'] >= 0.0
        assert seg['end_sec'] > seg['start_sec']
        assert seg['start_sec'] >= prev_end
        prev_end = seg['end_sec']


def test_duration_and_priority_integrity():
    cues = json.loads(Path(CONFIG['output_cues']).read_text())
    real_duration = probe_duration(CONFIG['output_audio'])
    assert real_duration > 10.0
    assert abs(real_duration - cues['total_duration_sec']) <= 7.0

    expected_priorities = [x['priority'] for x in SOURCE['updates']]
    actual_priorities = [x['priority'] for x in cues['segments']]
    assert actual_priorities == expected_priorities
