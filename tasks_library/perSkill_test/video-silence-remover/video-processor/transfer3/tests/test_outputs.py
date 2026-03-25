import importlib.util
import json
from pathlib import Path

CONFIG = json.loads(Path('/root/data/task_config.json').read_text())


def load_video_module():
    module_path = Path('/root/.codex/skills/video-processor/scripts/process_video.py')
    spec = importlib.util.spec_from_file_location('video_skill', module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_output_files_exist():
    assert Path(CONFIG['output_video']).exists(), f"Missing output video: {CONFIG['output_video']}"
    assert Path(CONFIG['report_json']).exists(), f"Missing report JSON: {CONFIG['report_json']}"
    assert Path(CONFIG['summary_json']).exists(), f"Missing summary JSON: {CONFIG['summary_json']}"


def test_report_matches_actual_output():
    module = load_video_module()
    report = json.loads(Path(CONFIG['report_json']).read_text())
    summary = json.loads(Path(CONFIG['summary_json']).read_text())

    total_duration = module.get_video_duration(CONFIG['input_video'])
    output_duration = module.get_video_duration(CONFIG['output_video'])
    remove_segments = module.load_segments(CONFIG['remove_segments'])
    keep_segments = module.calculate_keep_segments(remove_segments, total_duration)

    assert abs(report['original_duration'] - total_duration) <= 0.1
    assert abs(report['output_duration'] - output_duration) <= 0.1
    assert abs(report['removed_duration'] - (total_duration - output_duration)) <= 0.15
    assert report['segments_removed'] == len(remove_segments)
    assert report['segments_kept'] == len(keep_segments)

    expected_keep_duration = sum(segment['end'] - segment['start'] for segment in keep_segments)
    assert abs(output_duration - expected_keep_duration) <= 0.25

    expected_pct = round((total_duration - output_duration) / total_duration * 100, 2)
    assert abs(report['compression_percentage'] - expected_pct) <= 0.01

    assert summary['output_duration'] == report['output_duration']
    assert summary['removed_duration'] == report['removed_duration']
    assert summary['segments_removed'] == report['segments_removed']
    assert summary['segments_kept'] == report['segments_kept']


if __name__ == '__main__':
    test_output_files_exist()
    test_report_matches_actual_output()
