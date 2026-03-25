import json
import wave
from pathlib import Path

CONFIG = json.loads(Path('/root/data/task_config.json').read_text())


def read_summary():
    return json.loads(Path(CONFIG['summary_json']).read_text())


def test_output_files_exist():
    assert Path(CONFIG['output_wav']).exists(), f"Missing WAV output: {CONFIG['output_wav']}"
    assert Path(CONFIG['summary_json']).exists(), f"Missing summary output: {CONFIG['summary_json']}"


def test_audio_properties_match_config():
    with wave.open(CONFIG['output_wav'], 'rb') as wav_file:
        frame_count = wav_file.getnframes()
        sample_rate = wav_file.getframerate()
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()

    duration_seconds = frame_count / sample_rate if sample_rate else 0.0
    assert channels == CONFIG['expected_channels']
    assert sample_width == CONFIG['expected_sample_width']
    assert sample_rate == CONFIG['sample_rate']
    assert CONFIG['duration_min'] <= duration_seconds <= CONFIG['duration_max'], (
        f"Duration {duration_seconds:.3f}s outside expected range "
        f"[{CONFIG['duration_min']}, {CONFIG['duration_max']}]"
    )


def test_manifest_matches_wav():
    summary = read_summary()
    with wave.open(CONFIG['output_wav'], 'rb') as wav_file:
        frame_count = wav_file.getnframes()
        sample_rate = wav_file.getframerate()
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()

    duration_seconds = frame_count / sample_rate if sample_rate else 0.0
    assert summary['sample_rate'] == sample_rate
    assert summary['channels'] == channels
    assert summary['sample_width_bytes'] == sample_width
    assert summary['frame_count'] == frame_count
    assert abs(summary['duration_seconds'] - duration_seconds) <= 0.01


if __name__ == '__main__':
    test_output_files_exist()
    test_audio_properties_match_config()
    test_manifest_matches_wav()
