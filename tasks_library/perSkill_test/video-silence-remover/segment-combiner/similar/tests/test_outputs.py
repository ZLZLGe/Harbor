import importlib.util
import json
from pathlib import Path

CONFIG = json.loads(Path('/root/data/task_config.json').read_text())


def load_segment_module():
    module_path = Path('/root/.codex/skills/segment-combiner/scripts/combine_segments.py')
    spec = importlib.util.spec_from_file_location('segment_skill', module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_output_files_exist():
    assert Path(CONFIG['output_json']).exists(), f"Missing combined output: {CONFIG['output_json']}"
    assert Path(CONFIG['summary_json']).exists(), f"Missing summary output: {CONFIG['summary_json']}"


def test_combined_output_matches_skill_behavior():
    module = load_segment_module()
    payload = json.loads(Path(CONFIG['output_json']).read_text())
    expected = module.combine_segments(CONFIG['input_segments'])
    assert payload == expected


def test_summary_matches_combined_output():
    payload = json.loads(Path(CONFIG['output_json']).read_text())
    summary = json.loads(Path(CONFIG['summary_json']).read_text())
    segments = payload['segments']

    assert summary['segment_count'] == payload['total_segments']
    assert summary['total_duration_seconds'] == payload['total_duration_seconds']
    assert summary['first_segment_start'] == segments[0]['start']
    assert summary['last_segment_end'] == segments[-1]['end']


if __name__ == '__main__':
    test_output_files_exist()
    test_combined_output_matches_skill_behavior()
    test_summary_matches_combined_output()
