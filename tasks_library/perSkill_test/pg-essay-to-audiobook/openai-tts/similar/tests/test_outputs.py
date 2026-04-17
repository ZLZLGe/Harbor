import json
import subprocess
from pathlib import Path

CONFIG = json.loads(Path('/root/data/task_config.json').read_text())
SOURCE = json.loads(Path('/root/data/essay_fragments.json').read_text())


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
    assert Path(CONFIG['output_audio']).exists(), 'audio output missing'
    assert Path(CONFIG['output_manifest']).exists(), 'manifest output missing'


def test_manifest_structure_and_order():
    manifest = json.loads(Path(CONFIG['output_manifest']).read_text())
    assert manifest['voice'] == CONFIG['voice']
    assert manifest['model'] == CONFIG['model']
    chapters = manifest['chapters']
    assert len(chapters) == len(SOURCE['chapters'])

    expected_ids = [x['chapter_id'] for x in SOURCE['chapters']]
    actual_ids = [x['chapter_id'] for x in chapters]
    assert actual_ids == expected_ids

    for item in chapters:
        assert item['duration_sec'] > 2.0
        assert item['char_count'] > 250


def test_audio_duration_consistency():
    manifest = json.loads(Path(CONFIG['output_manifest']).read_text())
    real_duration = probe_duration(CONFIG['output_audio'])
    assert real_duration > 12.0
    assert abs(real_duration - manifest['total_duration_sec']) <= 6.0
