import csv
import json
import re
import subprocess
from pathlib import Path

CONFIG = json.loads(Path('/root/data/task_config.json').read_text())
MARKDOWN = Path('/root/data/release_notes.md').read_text()


def parse_sections(markdown: str):
    pattern = re.compile(r'^##\s+(.*)$', re.MULTILINE)
    return [m.group(1).strip() for m in pattern.finditer(markdown)]


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
    assert Path(CONFIG['output_markers']).exists()


def test_marker_csv_schema_and_order():
    rows = list(csv.DictReader(Path(CONFIG['output_markers']).read_text().splitlines()))
    assert rows, 'marker csv should not be empty'
    assert rows[0].keys() == {'section', 'start_sec', 'end_sec', 'word_count'}

    expected_sections = parse_sections(MARKDOWN)
    actual_sections = [r['section'] for r in rows]
    assert actual_sections == expected_sections

    prev_end = -1.0
    for row in rows:
        start = float(row['start_sec'])
        end = float(row['end_sec'])
        words = int(row['word_count'])
        assert start >= 0.0
        assert end > start
        assert start >= prev_end
        assert words >= 8
        prev_end = end


def test_duration_vs_markers():
    rows = list(csv.DictReader(Path(CONFIG['output_markers']).read_text().splitlines()))
    last_end = float(rows[-1]['end_sec'])
    duration = probe_duration(CONFIG['output_audio'])
    assert duration > 8.0
    assert duration + 1.5 >= last_end
