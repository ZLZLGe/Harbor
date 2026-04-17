#!/usr/bin/env python3
"""Deterministic local text-to-audio fallback synthesizer (WAV)."""

import argparse
import hashlib
import math
import wave

SAMPLE_RATE = 16000
AMPLITUDE = 12000


def estimate_duration(text: str) -> float:
    return max(0.6, min(5.0, 0.018 * len(text) + 0.45))


def pick_frequency(text: str) -> int:
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()
    return 240 + (int(digest[:4], 16) % 360)


def synthesize(text: str, output_path: str) -> None:
    duration = estimate_duration(text)
    freq = pick_frequency(text)
    total_frames = int(duration * SAMPLE_RATE)

    with wave.open(output_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        for i in range(total_frames):
            t = i / SAMPLE_RATE
            value = int(AMPLITUDE * math.sin(2.0 * math.pi * freq * t))
            wf.writeframesraw(value.to_bytes(2, byteorder="little", signed=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    synthesize(args.text, args.output)


if __name__ == "__main__":
    main()
