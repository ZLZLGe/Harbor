#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
import json
import math
import struct
import wave
from pathlib import Path

INPUT_PATH = Path("/root/dispatch_recording.wav")
POLICY_PATH = Path("/root/mask_policy.json")
OUTPUT_PATH = Path("/root/speech_activity_mask.csv")
SUMMARY_PATH = Path("/root/activity_summary.json")

FRAME_MS = 30
MIN_SEGMENT_SECONDS = 0.15
MAX_MERGE_GAP_SECONDS = 0.12


def load_policy():
    with POLICY_PATH.open() as handle:
        return json.load(handle)


def load_wav():
    with wave.open(str(INPUT_PATH), "rb") as wav_file:
        sample_rate = wav_file.getframerate()
        sample_width = wav_file.getsampwidth()
        channels = wav_file.getnchannels()
        frame_count = wav_file.getnframes()
        frames = wav_file.readframes(frame_count)
    if sample_width != 2 or channels != 1:
        raise ValueError("expected mono 16-bit PCM wav input")
    samples = struct.unpack("<{}h".format(len(frames) // 2), frames)
    return sample_rate, samples


def compute_frame_features(samples, sample_rate):
    frame_size = int(sample_rate * FRAME_MS / 1000)
    rms_values = []
    zero_crossings = []
    timestamps = []

    for index in range(0, len(samples) - frame_size + 1, frame_size):
        chunk = samples[index : index + frame_size]
        energy = sum(sample * sample for sample in chunk) / len(chunk)
        rms_values.append(math.sqrt(energy) / 32768.0)
        zc = sum(1 for left, right in zip(chunk, chunk[1:]) if (left >= 0) != (right >= 0))
        zero_crossings.append(zc / len(chunk))
        timestamps.append(index / sample_rate)

    return timestamps, rms_values, zero_crossings


def classify_frames(rms_values, zero_crossings):
    ordered = sorted(rms_values)
    noise_floor = ordered[int(len(ordered) * 0.3)]
    threshold = max(noise_floor * 2.8, 0.018)
    raw_flags = []
    for rms_value, zc_ratio in zip(rms_values, zero_crossings):
        raw_flags.append(rms_value >= threshold and zc_ratio < 0.20)

    smoothed_flags = []
    for index in range(len(raw_flags)):
        window = raw_flags[max(0, index - 1) : min(len(raw_flags), index + 2)]
        smoothed_flags.append(sum(window) >= 2)
    return smoothed_flags


def collect_segments(timestamps, flags):
    segments = []
    active_start = None
    frame_duration = FRAME_MS / 1000.0

    for timestamp, is_active in zip(timestamps, flags):
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

    merged = []
    for start, end in segments:
        if not merged or start - merged[-1][1] > MAX_MERGE_GAP_SECONDS:
            merged.append([start, end])
        else:
            merged[-1][1] = end
    return merged


def bucket_rows(policy, segments):
    bucket_size = float(policy["bucket_size_seconds"])
    total_duration = float(policy["timeline_duration_seconds"])
    activation_threshold = float(policy["speech_seconds_to_activate_bucket"])
    total_buckets = int(round(total_duration / bucket_size))

    rows = []
    for bucket_index in range(total_buckets):
        start = round(bucket_index * bucket_size, 3)
        end = round(start + bucket_size, 3)
        overlap = 0.0
        for seg_start, seg_end in segments:
            overlap += max(0.0, min(end, seg_end) - max(start, seg_start))
        rows.append(
            {
                "bucket_id": f"bucket_{bucket_index + 1:03d}",
                "start": start,
                "end": end,
                "speech_active": 1 if overlap + 1e-9 >= activation_threshold else 0,
            }
        )
    return rows


def write_csv(rows):
    with OUTPUT_PATH.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["bucket_id", "start", "end", "speech_active"])
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "bucket_id": row["bucket_id"],
                    "start": f"{row['start']:.3f}",
                    "end": f"{row['end']:.3f}",
                    "speech_active": row["speech_active"],
                }
            )


def write_summary(policy, rows):
    bucket_size = float(policy["bucket_size_seconds"])
    total_duration = float(policy["timeline_duration_seconds"])
    total_buckets = len(rows)
    active_buckets = sum(int(row["speech_active"]) for row in rows)
    summary = {
        "source_file": str(INPUT_PATH),
        "policy_file": str(POLICY_PATH),
        "bucket_size_seconds": bucket_size,
        "timeline_duration_seconds": total_duration,
        "total_buckets": total_buckets,
        "active_buckets": active_buckets,
        "inactive_buckets": total_buckets - active_buckets,
        "active_duration_seconds": round(active_buckets * bucket_size, 3),
        "active_ratio": round(active_buckets / total_buckets, 3),
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n")


policy = load_policy()
sample_rate, samples = load_wav()
timestamps, rms_values, zero_crossings = compute_frame_features(samples, sample_rate)
flags = classify_frames(rms_values, zero_crossings)
segments = collect_segments(timestamps, flags)
rows = bucket_rows(policy, segments)
write_csv(rows)
write_summary(policy, rows)
PY
