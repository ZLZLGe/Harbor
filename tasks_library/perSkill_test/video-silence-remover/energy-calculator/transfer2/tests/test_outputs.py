import json
import math
import wave
from array import array
from pathlib import Path

CONFIG = json.loads(Path('/root/data/task_config.json').read_text())


def read_samples(path):
    with wave.open(path, 'rb') as wav_file:
        sample_rate = wav_file.getframerate()
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        frame_count = wav_file.getnframes()
        raw = wav_file.readframes(frame_count)

    assert channels == 1, f'Expected mono WAV, found {channels} channels'
    assert sample_width == 2, f'Expected 16-bit WAV, found sample width {sample_width}'
    samples = array('h')
    samples.frombytes(raw)
    return sample_rate, list(samples)


def calculate_expected_energies():
    sample_rate, samples = read_samples(CONFIG['input_audio'])
    window_size = int(sample_rate * CONFIG['window_seconds'])
    energies = []
    for start in range(0, len(samples), window_size):
        window = samples[start : start + window_size]
        if not window:
            continue
        rms = math.sqrt(sum(sample * sample for sample in window) / len(window))
        energies.append(float(rms))
    return sample_rate, energies


def test_output_files_exist():
    assert Path(CONFIG['output_json']).exists(), f"Missing energy output: {CONFIG['output_json']}"
    assert Path(CONFIG['summary_json']).exists(), f"Missing summary output: {CONFIG['summary_json']}"


def test_energy_json_matches_input_audio():
    sample_rate, expected_energies = calculate_expected_energies()
    payload = json.loads(Path(CONFIG['output_json']).read_text())

    assert payload['sample_rate'] == sample_rate
    assert abs(payload['window_seconds'] - CONFIG['window_seconds']) <= 1e-9
    assert payload['total_seconds'] == len(expected_energies) * CONFIG['window_seconds']
    assert len(payload['energies']) == CONFIG['expected_window_count']
    assert len(payload['energies']) == len(expected_energies)

    for actual, expected in zip(payload['energies'], expected_energies):
        assert abs(actual - expected) <= 1e-3, f'Energy mismatch: {actual} vs {expected}'

    stats = payload['stats']
    assert abs(stats['min'] - min(expected_energies)) <= 1e-3
    assert abs(stats['max'] - max(expected_energies)) <= 1e-3
    assert abs(stats['mean'] - (sum(expected_energies) / len(expected_energies))) <= 1e-3
    variance = sum((value - stats['mean']) ** 2 for value in expected_energies) / len(expected_energies)
    assert abs(stats['std'] - math.sqrt(variance)) <= 1e-3


def test_summary_matches_energy_profile():
    payload = json.loads(Path(CONFIG['output_json']).read_text())
    summary = json.loads(Path(CONFIG['summary_json']).read_text())
    energies = payload['energies']

    assert summary['window_count'] == len(energies)
    assert summary['loudest_window_index'] == max(range(len(energies)), key=lambda idx: energies[idx])
    assert summary['quietest_window_index'] == min(range(len(energies)), key=lambda idx: energies[idx])
    assert summary['active_window_count'] == sum(1 for value in energies if value >= CONFIG['activity_threshold'])
    assert abs(summary['activity_threshold'] - CONFIG['activity_threshold']) <= 1e-9
    assert abs(summary['mean_energy'] - payload['stats']['mean']) <= 1e-9


if __name__ == '__main__':
    test_output_files_exist()
    test_energy_json_matches_input_audio()
    test_summary_matches_energy_profile()
