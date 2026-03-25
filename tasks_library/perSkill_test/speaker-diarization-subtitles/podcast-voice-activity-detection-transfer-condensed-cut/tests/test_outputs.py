import json
import math
import struct
import wave
from pathlib import Path


INPUT_PATH = Path("/root/raw_podcast.wav")
POLICY_PATH = Path("/root/edit_policy.json")
OUTPUT_PATH = Path("/root/condensed_podcast.wav")
REPORT_PATH = Path("/root/condense_report.json")
REFERENCE_PATH = Path("/tests/reference_regions.json")

BOUNDARY_TOLERANCE_SECONDS = 0.08
OUTPUT_DURATION_TOLERANCE_SECONDS = 0.02


def load_json(path: Path):
    with path.open() as handle:
        return json.load(handle)


def load_wav(path: Path):
    with wave.open(str(path), "rb") as wav_file:
        params = {
            "channels": wav_file.getnchannels(),
            "sample_width": wav_file.getsampwidth(),
            "sample_rate": wav_file.getframerate(),
            "frame_count": wav_file.getnframes(),
        }
        frames = wav_file.readframes(params["frame_count"])
    samples = struct.unpack("<{}h".format(len(frames) // 2), frames)
    return params, samples


def rounded_duration(start: float, end: float) -> float:
    return round(round(end, 3) - round(start, 3), 3)


def concat_regions(samples, sample_rate, regions):
    output = []
    for region in regions:
        start_index = max(0, int(round(float(region["start"]) * sample_rate)))
        end_index = min(len(samples), int(round(float(region["end"]) * sample_rate)))
        output.extend(samples[start_index:end_index])
    return output


def test_required_files_exist():
    assert OUTPUT_PATH.exists(), "缺少 /root/condensed_podcast.wav"
    assert REPORT_PATH.exists(), "缺少 /root/condense_report.json"


def test_report_structure_and_summary_consistency():
    report = load_json(REPORT_PATH)
    policy = load_json(POLICY_PATH)
    output_params, output_samples = load_wav(OUTPUT_PATH)

    assert report["source_file"] == str(INPUT_PATH)
    assert report["output_file"] == str(OUTPUT_PATH)
    assert isinstance(report["kept_regions"], list) and report["kept_regions"], "kept_regions 不能为空"

    assert output_params["channels"] == int(policy["target_channels"])
    assert output_params["sample_width"] == int(policy["target_sample_width_bytes"])
    assert output_params["sample_rate"] == int(policy["target_sample_rate_hz"])

    previous_end = -1.0
    for region in report["kept_regions"]:
        assert set(region.keys()) == {"start", "end", "duration"}
        start = float(region["start"])
        end = float(region["end"])
        duration = float(region["duration"])
        assert 0 <= start < end
        assert start >= previous_end
        assert math.isclose(duration, rounded_duration(start, end), abs_tol=0.001)
        previous_end = end

    summary = report["summary"]
    assert summary["segment_count"] == len(report["kept_regions"])
    assert math.isclose(float(summary["merge_gap_seconds"]), float(policy["merge_gap_seconds"]), abs_tol=1e-6)
    assert math.isclose(float(summary["padding_seconds"]), float(policy["padding_seconds"]), abs_tol=1e-6)

    input_params, _ = load_wav(INPUT_PATH)
    input_duration = input_params["frame_count"] / input_params["sample_rate"]
    actual_output_duration = output_params["frame_count"] / output_params["sample_rate"]
    reported_output_duration = float(summary["output_duration_sec"])
    expected_output_duration = round(sum(float(item["duration"]) for item in report["kept_regions"]), 3)

    assert math.isclose(float(summary["input_duration_sec"]), round(input_duration, 3), abs_tol=0.001)
    assert math.isclose(reported_output_duration, round(actual_output_duration, 3), abs_tol=OUTPUT_DURATION_TOLERANCE_SECONDS)
    assert math.isclose(reported_output_duration, expected_output_duration, abs_tol=0.02)
    assert math.isclose(
        float(summary["removed_silence_sec"]),
        round(float(summary["input_duration_sec"]) - reported_output_duration, 3),
        abs_tol=0.02,
    )


def test_kept_regions_match_expected_edit_semantics():
    report = load_json(REPORT_PATH)
    reference = load_json(REFERENCE_PATH)

    predicted_regions = report["kept_regions"]
    expected_regions = reference["kept_regions"]

    assert len(predicted_regions) == len(expected_regions)

    for predicted, expected in zip(predicted_regions, expected_regions):
        assert abs(float(predicted["start"]) - float(expected["start"])) <= BOUNDARY_TOLERANCE_SECONDS
        assert abs(float(predicted["end"]) - float(expected["end"])) <= BOUNDARY_TOLERANCE_SECONDS
        assert abs(float(predicted["duration"]) - float(expected["duration"])) <= BOUNDARY_TOLERANCE_SECONDS * 2


def test_output_audio_is_exact_concatenation_of_reported_regions():
    report = load_json(REPORT_PATH)
    input_params, input_samples = load_wav(INPUT_PATH)
    output_params, output_samples = load_wav(OUTPUT_PATH)

    expected_samples = concat_regions(input_samples, input_params["sample_rate"], report["kept_regions"])

    assert output_params["sample_rate"] == input_params["sample_rate"]
    assert abs(len(output_samples) - len(expected_samples)) <= 2

    overlap = min(len(output_samples), len(expected_samples))
    max_abs_diff = 0
    for actual, expected in zip(output_samples[:overlap], expected_samples[:overlap]):
        max_abs_diff = max(max_abs_diff, abs(actual - expected))

    assert max_abs_diff <= 1, f"output waveform mismatch: max abs diff = {max_abs_diff}"
