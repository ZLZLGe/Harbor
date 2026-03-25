import importlib.util
import json
from pathlib import Path

CONFIG = json.loads(Path('/root/data/task_config.json').read_text())


def load_report_module():
    module_path = Path('/root/.codex/skills/report-generator/scripts/generate_report.py')
    spec = importlib.util.spec_from_file_location('report_skill', module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_output_files_exist():
    assert Path(CONFIG['output_json']).exists(), f"Missing report output: {CONFIG['output_json']}"
    assert Path(CONFIG['summary_json']).exists(), f"Missing summary output: {CONFIG['summary_json']}"


def test_report_matches_skill_behavior():
    module = load_report_module()
    payload = json.loads(Path(CONFIG['output_json']).read_text())
    expected = module.generate_report(
        CONFIG['original_video'],
        CONFIG['compressed_video'],
        CONFIG['segments_json'],
    )
    assert payload == expected


def test_summary_matches_report():
    payload = json.loads(Path(CONFIG['output_json']).read_text())
    summary = json.loads(Path(CONFIG['summary_json']).read_text())
    segment_data = json.loads(Path(CONFIG['segments_json']).read_text())
    segments = segment_data['segments']

    assert summary['segment_count'] == len(segments)
    assert summary['removed_duration_seconds'] == payload['removed_duration_seconds']
    assert summary['compression_percentage'] == payload['compression_percentage']
    assert summary['longest_segment_duration'] == max(segment['duration'] for segment in segments)
    assert summary['segment_total_duration_seconds'] == sum(segment['duration'] for segment in segments)


if __name__ == '__main__':
    test_output_files_exist()
    test_report_matches_skill_behavior()
    test_summary_matches_report()
