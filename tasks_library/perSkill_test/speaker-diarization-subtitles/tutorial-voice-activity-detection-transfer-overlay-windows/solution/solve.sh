#!/bin/bash
set -euo pipefail

ffmpeg -y -i /root/tutorial_walkthrough.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 /tmp/tutorial_audio.wav >/tmp/overlay_ffmpeg.log 2>&1

python3 <<'PY'
import csv
import json
import wave
from pathlib import Path

import webrtcvad

INPUT_WAV = Path("/tmp/tutorial_audio.wav")
POLICY_PATH = Path("/root/overlay_policy.json")
OUTPUT_PATH = Path("/root/overlay_windows.csv")
FRAME_MS = 30
MIN_RAW_SPEECH_SECONDS = 0.24


def load_policy():
    with POLICY_PATH.open() as handle:
        return json.load(handle)


def read_wave(path: Path):
    with wave.open(str(path), "rb") as wav_file:
        sample_rate = wav_file.getframerate()
        sample_width = wav_file.getsampwidth()
        channels = wav_file.getnchannels()
        if sample_width != 2:
            raise ValueError("expected 16-bit PCM audio")
        if channels != 1:
            raise ValueError("expected mono audio")
        pcm_data = wav_file.readframes(wav_file.getnframes())
    return pcm_data, sample_rate


def make_frames(pcm_data: bytes, sample_rate: int):
    frame_size = int(sample_rate * FRAME_MS / 1000.0) * 2
    frame_duration = FRAME_MS / 1000.0
    timestamp = 0.0
    frames = []
    for offset in range(0, len(pcm_data) - frame_size + 1, frame_size):
        frames.append((timestamp, frame_duration, pcm_data[offset : offset + frame_size]))
        timestamp += frame_duration
    return frames


def smooth_flags(flags):
    if len(flags) < 3:
        return flags[:]
    smoothed = []
    for index in range(len(flags)):
        left = max(0, index - 1)
        right = min(len(flags), index + 2)
        window = flags[left:right]
        smoothed.append(sum(window) >= max(1, len(window) - 1))
    return smoothed


def detect_speech_segments(frames, sample_rate: int):
    vad = webrtcvad.Vad(2)
    raw_flags = [vad.is_speech(frame_bytes, sample_rate) for _, _, frame_bytes in frames]
    flags = smooth_flags(raw_flags)

    segments = []
    active_start = None
    active_end = None

    for (timestamp, duration, _), is_speech in zip(frames, flags):
        if is_speech:
            if active_start is None:
                active_start = timestamp
            active_end = timestamp + duration
        elif active_start is not None and active_end is not None:
            if active_end - active_start >= MIN_RAW_SPEECH_SECONDS:
                segments.append((active_start, active_end))
            active_start = None
            active_end = None

    if active_start is not None and active_end is not None and active_end - active_start >= MIN_RAW_SPEECH_SECONDS:
        segments.append((active_start, active_end))

    return segments


def merge_segments(segments, max_gap: float):
    if not segments:
        return []
    merged = [list(segments[0])]
    for start, end in segments[1:]:
        if start - merged[-1][1] <= max_gap:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(start, end) for start, end in merged]


def protect_segments(segments, guard: float, timeline_end: float):
    protected = []
    for start, end in segments:
        bounded_start = max(0.0, start - guard)
        bounded_end = min(timeline_end, end + guard)
        if not protected or bounded_start > protected[-1][1]:
            protected.append([bounded_start, bounded_end])
        else:
            protected[-1][1] = max(protected[-1][1], bounded_end)
    return [(start, end) for start, end in protected]


def complement_segments(segments, timeline_end: float):
    if not segments:
        return [(0.0, timeline_end)]
    windows = []
    cursor = 0.0
    for start, end in segments:
        if start > cursor:
            windows.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < timeline_end:
        windows.append((cursor, timeline_end))
    return windows


def normalize_ranges(ranges, timeline_end: float):
    normalized = []
    for item in ranges:
        start = max(0.0, float(item["start"]))
        end = min(timeline_end, float(item["end"]))
        if end <= start:
            continue
        if not normalized or start > normalized[-1][1]:
            normalized.append([start, end])
        else:
            normalized[-1][1] = max(normalized[-1][1], end)
    return [(start, end) for start, end in normalized]


def subtract_ranges(windows, blocked_ranges):
    trimmed = []
    for window_start, window_end in windows:
        remaining = [(window_start, window_end)]
        for block_start, block_end in blocked_ranges:
            next_remaining = []
            for start, end in remaining:
                if block_end <= start or block_start >= end:
                    next_remaining.append((start, end))
                    continue
                if start < block_start:
                    next_remaining.append((start, block_start))
                if block_end < end:
                    next_remaining.append((block_end, end))
            remaining = next_remaining
            if not remaining:
                break
        trimmed.extend(remaining)
    return trimmed


def round_triplet(start: float, end: float):
    rounded_start = round(start, 3)
    rounded_end = round(end, 3)
    return rounded_start, rounded_end, round(rounded_end - rounded_start, 3)


def write_csv(rows):
    with OUTPUT_PATH.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["window_id", "start", "end", "duration"])
        for index, (start, end, duration) in enumerate(rows, start=1):
            writer.writerow([f"overlay_{index:02d}", f"{start:.3f}", f"{end:.3f}", f"{duration:.3f}"])


policy = load_policy()
pcm_data, sample_rate = read_wave(INPUT_WAV)
frames = make_frames(pcm_data, sample_rate)
speech_segments = detect_speech_segments(frames, sample_rate)
merged_speech = merge_segments(speech_segments, float(policy["merge_gap_seconds"]))
protected_speech = protect_segments(
    merged_speech,
    float(policy["speech_guard_seconds"]),
    float(policy["timeline_duration_seconds"]),
)
candidate_windows = complement_segments(protected_speech, float(policy["timeline_duration_seconds"]))
usable_windows = subtract_ranges(
    candidate_windows,
    normalize_ranges(policy["blocked_ranges"], float(policy["timeline_duration_seconds"])),
)
overlay_windows = []
for start, end in usable_windows:
    rounded_start, rounded_end, duration = round_triplet(start, end)
    if duration >= float(policy["min_window_seconds"]):
        overlay_windows.append((rounded_start, rounded_end, duration))

write_csv(overlay_windows)
PY
