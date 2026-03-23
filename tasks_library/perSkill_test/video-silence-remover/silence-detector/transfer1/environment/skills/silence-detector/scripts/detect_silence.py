#!/usr/bin/env python3
"""
Silence detector - finds initial silence segment using energy data.
Detects low-energy periods at the start of audio (e.g., title slides, setup time).
Pure Python implementation to avoid third-party runtime dependencies.
"""

import argparse
import json


def moving_average(values, window):
    if window <= 1:
        return list(values)
    if len(values) < window:
        return list(values)
    out = []
    for i in range(len(values) - window + 1):
        out.append(sum(values[i : i + window]) / window)
    return out


def detect_initial_silence(energies, threshold_multiplier=1.5, initial_window=60, smoothing_window=30):
    """Detect initial silence using energy threshold method."""
    energies = [float(v) for v in energies]
    if not energies:
        return 0, {"initial_avg": 0.0, "threshold": 0.0}

    baseline_count = min(initial_window, len(energies))
    initial_avg = sum(energies[:baseline_count]) / baseline_count
    threshold = initial_avg * float(threshold_multiplier)

    smoothed = moving_average(energies, int(smoothing_window))

    silence_end = 0
    for idx, value in enumerate(smoothed):
        if value > threshold:
            silence_end = idx
            break

    return silence_end, {"initial_avg": float(initial_avg), "threshold": float(threshold)}


def main():
    parser = argparse.ArgumentParser(description="Detect initial silence from energy data")
    parser.add_argument("--energies", required=True, help="Path to energy JSON file")
    parser.add_argument("--output", required=True, help="Path to output JSON file")
    parser.add_argument("--threshold-multiplier", type=float, default=1.5, help="Threshold multiplier (default: 1.5)")
    parser.add_argument("--initial-window", type=int, default=60, help="Initial window for baseline (default: 60)")
    parser.add_argument("--smoothing-window", type=int, default=30, help="Smoothing window (default: 30)")

    args = parser.parse_args()

    with open(args.energies, "r", encoding="utf-8") as f:
        energy_data = json.load(f)

    energies = energy_data["energies"]

    silence_end, analysis = detect_initial_silence(
        energies,
        args.threshold_multiplier,
        args.initial_window,
        args.smoothing_window,
    )

    segments = []
    if silence_end > 0:
        segments.append({"start": 0, "end": silence_end, "duration": silence_end})

    result = {
        "method": "energy_threshold",
        "segments": segments,
        "total_segments": len(segments),
        "total_duration_seconds": silence_end if silence_end > 0 else 0,
        "parameters": {
            "threshold_multiplier": args.threshold_multiplier,
            "initial_window": args.initial_window,
            "smoothing_window": args.smoothing_window,
        },
        "analysis": analysis,
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)


if __name__ == "__main__":
    main()
