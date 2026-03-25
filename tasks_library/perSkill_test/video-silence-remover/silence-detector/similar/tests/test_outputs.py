import importlib.util
import json
from pathlib import Path

CONFIG = json.loads(Path('/root/data/task_config.json').read_text())


def load_silence_module():
    module_path = Path('/root/.codex/skills/silence-detector/scripts/detect_silence.py')
    spec = importlib.util.spec_from_file_location('silence_skill', module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_output_files_exist():
    assert Path(CONFIG['output_json']).exists(), f"Missing silence output: {CONFIG['output_json']}"
    assert Path(CONFIG['summary_json']).exists(), f"Missing summary output: {CONFIG['summary_json']}"


def test_silence_output_matches_skill_behavior():
    module = load_silence_module()
    energy_payload = json.loads(Path(CONFIG['input_energies']).read_text())
    payload = json.loads(Path(CONFIG['output_json']).read_text())

    silence_end, analysis = module.detect_initial_silence(
        energy_payload['energies'],
        CONFIG['threshold_multiplier'],
        CONFIG['initial_window'],
        CONFIG['smoothing_window'],
    )

    expected_segments = []
    if silence_end > 0:
        expected_segments.append({'start': 0, 'end': silence_end, 'duration': silence_end})

    assert payload['method'] == 'energy_threshold'
    assert payload['segments'] == expected_segments
    assert payload['total_segments'] == len(expected_segments)
    assert payload['total_duration_seconds'] == silence_end if silence_end > 0 else 0
    assert payload['parameters']['threshold_multiplier'] == CONFIG['threshold_multiplier']
    assert payload['parameters']['initial_window'] == CONFIG['initial_window']
    assert payload['parameters']['smoothing_window'] == CONFIG['smoothing_window']
    assert payload['analysis']['initial_avg'] == analysis['initial_avg']
    assert payload['analysis']['threshold'] == analysis['threshold']


def test_summary_matches_silence_output():
    payload = json.loads(Path(CONFIG['output_json']).read_text())
    summary = json.loads(Path(CONFIG['summary_json']).read_text())

    assert summary['detected_silence_end'] == payload['total_duration_seconds']
    assert summary['baseline_energy'] == payload['analysis']['initial_avg']
    assert summary['threshold'] == payload['analysis']['threshold']
    assert summary['has_initial_silence'] == (payload['total_segments'] > 0)


if __name__ == '__main__':
    test_output_files_exist()
    test_silence_output_matches_skill_behavior()
    test_summary_matches_silence_output()
