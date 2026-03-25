#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import math
import struct
import wave
from pathlib import Path

INPUT_PATH = Path("/root/raw_podcast.wav")
POLICY_PATH = Path("/root/edit_policy.json")
OUTPUT_PATH = Path("/root/condensed_podcast.wav")
REPORT_PATH = Path("/root/condense_report.json")


def load_wav(path: Path):
    with wave.open(str(path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        frame_count = wav_file.getnframes()
        frames = wav_file.readframes(frame_count)
    if channels != 1 or sample_width != 2:
        raise ValueError("input wav must be mono 16-bit PCM")
    samples = struct.unpack("<{}h".format(len(frames) // 2), frames)
    return sample_rate, samples


def detect_active_regions(samples, sample_rate):
    frame_duration = 0.03
    frame_size = int(sample_rate * frame_duration)
    rms_values = []

    for start in range(0, len(samples), frame_size):
        chunk = samples[start : start + frame_size]
        if not chunk:
            continue
        energy = sum(sample * sample for sample in chunk) / len(chunk)
        rms_values.append(math.sqrt(energy) / 32768.0)

    ordered = sorted(rms_values)
    noise_floor = ordered[max(0, int(len(ordered) * 0.2) - 1)]
    threshold = max(noise_floor * 4.5, 0.012)

    regions = []
    active_start = None
    for index, rms_value in enumerate(rms_values):
        timestamp = index * frame_duration
        if rms_value >= threshold and active_start is None:
            active_start = timestamp
        elif rms_value < threshold and active_start is not None:
            regions.append([active_start, timestamp])
            active_start = None

    if active_start is not None:
        regions.append([active_start, len(rms_values) * frame_duration])

    return regions


def merge_regions(regions, gap_seconds):
    merged = []
    for start, end in regions:
        if end <= start:
            continue
        if not merged or start - merged[-1][1] > gap_seconds:
            merged.append([start, end])
        else:
            merged[-1][1] = end
    return merged


def add_padding(regions, padding_seconds, audio_duration):
    padded = []
    for start, end in regions:
        padded_start = max(0.0, start - padding_seconds)
        padded_end = min(audio_duration, end + padding_seconds)
        padded.append([padded_start, padded_end])
    return padded


def cut_and_concat(samples, sample_rate, regions):
    output_samples = []
    for start, end in regions:
        start_index = max(0, int(round(start * sample_rate)))
        end_index = min(len(samples), int(round(end * sample_rate)))
        output_samples.extend(samples[start_index:end_index])
    return output_samples


def round_region(region):
    start, end = region
    start = round(start, 3)
    end = round(end, 3)
    return {
        "start": start,
        "end": end,
        "duration": round(end - start, 3),
    }


policy = json.loads(POLICY_PATH.read_text())
sample_rate, samples = load_wav(INPUT_PATH)
audio_duration = len(samples) / sample_rate

regions = detect_active_regions(samples, sample_rate)
regions = merge_regions(regions, float(policy["merge_gap_seconds"]))
regions = add_padding(regions, float(policy["padding_seconds"]), audio_duration)

report_regions = [round_region(region) for region in regions]
output_samples = cut_and_concat(
    samples,
    sample_rate,
    [(region["start"], region["end"]) for region in report_regions],
)
output_frames = struct.pack("<{}h".format(len(output_samples)), *output_samples)

with wave.open(str(OUTPUT_PATH), "wb") as wav_file:
    wav_file.setnchannels(1)
    wav_file.setsampwidth(2)
    wav_file.setframerate(sample_rate)
    wav_file.writeframes(output_frames)

output_duration = len(output_samples) / sample_rate
report = {
    "source_file": str(INPUT_PATH),
    "output_file": str(OUTPUT_PATH),
    "kept_regions": report_regions,
    "summary": {
        "segment_count": len(report_regions),
        "input_duration_sec": round(audio_duration, 3),
        "output_duration_sec": round(output_duration, 3),
        "removed_silence_sec": round(audio_duration - output_duration, 3),
        "merge_gap_seconds": float(policy["merge_gap_seconds"]),
        "padding_seconds": float(policy["padding_seconds"]),
    },
}
REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n")
PY
