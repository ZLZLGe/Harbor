import importlib.util
import json
from pathlib import Path

CONFIG = json.loads(Path('/root/data/task_config.json').read_text())


def load_pause_module():
    module_path = Path('/root/.codex/skills/pause-detector/scripts/detect_pauses.py')
    spec = importlib.util.spec_from_file_location('pause_skill', module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_output_files_exist():
    assert Path(CONFIG['output_json']).exists(), f"Missing pause output: {CONFIG['output_json']}"
    assert Path(CONFIG['summary_json']).exists(), f"Missing summary output: {CONFIG['summary_json']}"


def test_pause_output_matches_skill_behavior():
    module = load_pause_module()
    energy_payload = json.loads(Path(CONFIG['input_energies']).read_text())
    payload = json.loads(Path(CONFIG['output_json']).read_text())

    expected_segments = module.detect_pauses(
        energy_payload['energies'],
        CONFIG['start_time'],
        CONFIG['threshold_ratio'],
        CONFIG['min_duration'],
        CONFIG['window_size'],
    )

    assert payload['method'] == 'local_dynamic_threshold'
    assert payload['segments'] == expected_segments
    assert payload['total_segments'] == len(expected_segments)
    assert payload['total_duration_seconds'] == sum(segment['duration'] for segment in expected_segments)
    assert payload['parameters']['threshold_ratio'] == CONFIG['threshold_ratio']
    assert payload['parameters']['window_size'] == CONFIG['window_size']
    assert payload['parameters']['min_duration'] == CONFIG['min_duration']
    assert payload['parameters']['start_time'] == CONFIG['start_time']


def test_summary_matches_pause_output():
    payload = json.loads(Path(CONFIG['output_json']).read_text())
    summary = json.loads(Path(CONFIG['summary_json']).read_text())
    segments = payload['segments']

    longest = max(segments, key=lambda segment: (segment['duration'], -segment['start']))
    assert summary['pause_count'] == payload['total_segments']
    assert summary['total_pause_duration'] == payload['total_duration_seconds']
    assert summary['longest_pause_start'] == longest['start']
    assert summary['longest_pause_duration'] == longest['duration']
    assert summary['analysis_start_time'] == CONFIG['start_time']


if __name__ == '__main__':
    test_output_files_exist()
    test_pause_output_matches_skill_behavior()
    test_summary_matches_pause_output()
