import csv
import json
import subprocess
from collections import Counter
from pathlib import Path

CONFIG = json.loads(Path('/root/data/task_config.json').read_text())
ROWS = list(csv.DictReader(Path('/root/data/call_snippets.csv').read_text().splitlines()))


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
    assert Path(CONFIG['output_report']).exists()


def test_report_fields_and_counts():
    report = json.loads(Path(CONFIG['output_report']).read_text())
    assert report['rows_processed'] == len(ROWS)
    assert report['voice'] == CONFIG['voice']
    assert report['model'] == CONFIG['model']

    expected = Counter([r['priority'].strip().lower() for r in ROWS])
    assert report['priority_counts'] == dict(sorted(expected.items()))


def test_audio_duration_and_size():
    report = json.loads(Path(CONFIG['output_report']).read_text())
    output = Path(CONFIG['output_audio'])
    assert output.stat().st_size > 10000

    real_duration = probe_duration(CONFIG['output_audio'])
    assert real_duration > 8.0
    assert abs(real_duration - report['total_duration_sec']) <= 6.0
