import csv
import json
import math
import struct
import wave
from pathlib import Path


OUTPUT_PATH = Path("/root/speech_activity_mask.csv")
SUMMARY_PATH = Path("/root/activity_summary.json")
POLICY_PATH = Path("/root/mask_policy.json")
INPUT_PATH = Path("/root/dispatch_recording.wav")

EXPECTED_COLUMNS = ["bucket_id", "start", "end", "speech_active"]
FRAME_MS = 30
MIN_SEGMENT_SECONDS = 0.15
MAX_MERGE_GAP_SECONDS = 0.12


def load_json(path: Path):
    with path.open() as handle:
        return json.load(handle)


def load_rows():
    with OUTPUT_PATH.open(newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == EXPECTED_COLUMNS, "CSV 表头必须为 bucket_id,start,end,speech_active"
        return list(reader)


def load_wav():
    with wave.open(str(INPUT_PATH), "rb") as wav_file:
        sample_rate = wav_file.getframerate()
        sample_width = wav_file.getsampwidth()
        channels = wav_file.getnchannels()
        frame_count = wav_file.getnframes()
        frames = wav_file.readframes(frame_count)

    assert sample_width == 2 and channels == 1, "测试录音必须是单声道 16-bit PCM wav"
    samples = struct.unpack("<{}h".format(len(frames) // 2), frames)
    return sample_rate, samples


def derive_reference_segments():
    sample_rate, samples = load_wav()
    frame_size = int(sample_rate * FRAME_MS / 1000)

    rms_values = []
    zero_crossings = []
    timestamps = []
    for index in range(0, len(samples) - frame_size + 1, frame_size):
        chunk = samples[index : index + frame_size]
        energy = sum(sample * sample for sample in chunk) / len(chunk)
        rms_values.append(math.sqrt(energy) / 32768.0)
        zero_crossings.append(
            sum(1 for left, right in zip(chunk, chunk[1:]) if (left >= 0) != (right >= 0)) / len(chunk)
        )
        timestamps.append(index / sample_rate)

    ordered_rms = sorted(rms_values)
    noise_floor = ordered_rms[int(len(ordered_rms) * 0.3)]
    threshold = max(noise_floor * 2.8, 0.018)

    raw_flags = []
    for rms_value, zc_ratio in zip(rms_values, zero_crossings):
        raw_flags.append(rms_value >= threshold and zc_ratio < 0.20)

    smoothed_flags = []
    for index in range(len(raw_flags)):
        window = raw_flags[max(0, index - 1) : min(len(raw_flags), index + 2)]
        smoothed_flags.append(sum(window) >= 2)

    segments = []
    active_start = None
    frame_duration = FRAME_MS / 1000.0
    for timestamp, is_active in zip(timestamps, smoothed_flags):
        if is_active and active_start is None:
            active_start = timestamp
        elif not is_active and active_start is not None:
            end_time = timestamp
            if end_time - active_start >= MIN_SEGMENT_SECONDS:
                segments.append([active_start, end_time])
            active_start = None

    if active_start is not None:
        end_time = timestamps[-1] + frame_duration
        if end_time - active_start >= MIN_SEGMENT_SECONDS:
            segments.append([active_start, end_time])

    merged_segments = []
    for start, end in segments:
        if not merged_segments or start - merged_segments[-1][1] > MAX_MERGE_GAP_SECONDS:
            merged_segments.append([start, end])
        else:
            merged_segments[-1][1] = end
    return merged_segments


def expected_mask(policy, speech_segments):
    bucket_size = float(policy["bucket_size_seconds"])
    timeline_duration = float(policy["timeline_duration_seconds"])
    activation_threshold = float(policy["speech_seconds_to_activate_bucket"])
    total_buckets = int(round(timeline_duration / bucket_size))

    mask = []
    for bucket_index in range(total_buckets):
        start = bucket_index * bucket_size
        end = start + bucket_size
        overlap = 0.0
        for interval in speech_segments:
            overlap += max(
                0.0,
                min(end, float(interval["end"])) - max(start, float(interval["start"])),
            )
        mask.append(1 if overlap + 1e-9 >= activation_threshold else 0)
    return mask


def precision_recall(reference_mask, predicted_mask):
    true_positive = sum(1 for ref, pred in zip(reference_mask, predicted_mask) if ref == pred == 1)
    false_positive = sum(1 for ref, pred in zip(reference_mask, predicted_mask) if ref == 0 and pred == 1)
    false_negative = sum(1 for ref, pred in zip(reference_mask, predicted_mask) if ref == 1 and pred == 0)

    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    return precision, recall


def test_required_outputs_exist():
    assert OUTPUT_PATH.exists(), "缺少 /root/speech_activity_mask.csv"
    assert SUMMARY_PATH.exists(), "缺少 /root/activity_summary.json"


def test_csv_structure_matches_policy():
    policy = load_json(POLICY_PATH)
    rows = load_rows()

    bucket_size = float(policy["bucket_size_seconds"])
    timeline_duration = float(policy["timeline_duration_seconds"])
    expected_count = int(round(timeline_duration / bucket_size))

    assert len(rows) == expected_count, "时间桶数量不符合 policy"

    previous_end = 0.0
    for index, row in enumerate(rows, start=1):
        start = float(row["start"])
        end = float(row["end"])
        speech_active = int(row["speech_active"])

        assert row["bucket_id"] == f"bucket_{index:03d}"
        assert speech_active in (0, 1)
        assert math.isclose(end - start, bucket_size, abs_tol=0.001)
        if index == 1:
            assert math.isclose(start, 0.0, abs_tol=0.001)
        else:
            assert math.isclose(start, previous_end, abs_tol=0.001)
        previous_end = end

    assert math.isclose(float(rows[-1]["end"]), timeline_duration, abs_tol=0.001)


def test_summary_is_consistent_with_csv():
    policy = load_json(POLICY_PATH)
    summary = load_json(SUMMARY_PATH)
    rows = load_rows()

    bucket_size = float(policy["bucket_size_seconds"])
    timeline_duration = float(policy["timeline_duration_seconds"])
    total_buckets = len(rows)
    active_buckets = sum(int(row["speech_active"]) for row in rows)

    assert summary["source_file"] == "/root/dispatch_recording.wav"
    assert summary["policy_file"] == "/root/mask_policy.json"
    assert math.isclose(float(summary["bucket_size_seconds"]), bucket_size, abs_tol=1e-6)
    assert math.isclose(float(summary["timeline_duration_seconds"]), timeline_duration, abs_tol=1e-6)
    assert int(summary["total_buckets"]) == total_buckets
    assert int(summary["active_buckets"]) == active_buckets
    assert int(summary["inactive_buckets"]) == total_buckets - active_buckets
    assert math.isclose(float(summary["active_duration_seconds"]), active_buckets * bucket_size, abs_tol=0.001)
    assert math.isclose(float(summary["active_ratio"]), round(active_buckets / total_buckets, 3), abs_tol=0.001)


def test_mask_matches_reference_semantics():
    policy = load_json(POLICY_PATH)
    rows = load_rows()

    predicted_mask = [int(row["speech_active"]) for row in rows]
    reference_segments = [
        {"start": start, "end": end}
        for start, end in derive_reference_segments()
    ]
    reference_mask = expected_mask(policy, reference_segments)

    assert len(predicted_mask) == len(reference_mask)

    precision, recall = precision_recall(reference_mask, predicted_mask)
    mismatches = sum(1 for ref, pred in zip(reference_mask, predicted_mask) if ref != pred)

    assert precision >= 0.95, f"bucket precision too low: {precision:.3f}"
    assert recall >= 0.95, f"bucket recall too low: {recall:.3f}"
    assert mismatches <= 1, f"too many mismatched buckets: {mismatches}"

    predicted_active = sum(predicted_mask)
    reference_active = sum(reference_mask)
    assert abs(predicted_active - reference_active) <= 1
