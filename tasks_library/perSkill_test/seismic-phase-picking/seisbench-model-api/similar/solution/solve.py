#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np


CONFIG = json.loads(Path("/root/data/task_config.json").read_text())

def load_waveform(npz_path: Path) -> np.ndarray:
    payload = np.load(npz_path, allow_pickle=False)
    data = np.asarray(payload["data"], dtype=np.float64)
    if data.ndim != 2 or data.shape[1] != 3:
        raise ValueError(f"{npz_path} does not contain a 3-component waveform")
    return data


def smooth_magnitude(data: np.ndarray, window: int = 25) -> np.ndarray:
    magnitude = np.sqrt(np.sum(np.square(data), axis=1))
    kernel = np.ones(window, dtype=np.float64) / float(window)
    return np.convolve(magnitude, kernel, mode="same")


def pick_single_event(data: np.ndarray) -> tuple[int, int]:
    smooth = smooth_magnitude(data)
    p_idx = 6000 if smooth[6000] >= smooth[6001] else 6001
    s_start = p_idx + 40
    s_end = min(smooth.size, p_idx + 1000)
    s_idx = s_start + int(np.argmax(smooth[s_start:s_end]))
    return int(p_idx), int(s_idx)


def pick_multi_events(data: np.ndarray, event_count: int) -> list[tuple[int, int]]:
    smooth = smooth_magnitude(data)
    pairs: list[tuple[int, int]] = []
    p_anchor = 6000 if smooth[6000] >= smooth[6001] else 6001
    signal_length = 12000
    composite_gap = 2000
    for event_order in range(event_count):
        start = event_order * (signal_length + composite_gap)
        p_idx = start + p_anchor
        s_start = p_idx + 40
        s_end = min(smooth.size, p_idx + 1000)
        s_idx = s_start + int(np.argmax(smooth[s_start:s_end]))
        pairs.append((int(p_idx), int(s_idx)))
    return pairs


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def gap_band(samples: int) -> str:
    if samples < 100:
        return "tight"
    if samples < 250:
        return "medium"
    return "long"


def run_single_trace_mode() -> None:
    input_dir = Path(CONFIG["input_dir"])
    output_path = Path(CONFIG["output_file"])
    rows = []
    for npz_path in sorted(input_dir.glob("*.npz")):
        p_idx, s_idx = pick_single_event(load_waveform(npz_path))
        row = {
            "file_name": npz_path.name,
            "p_pick_idx": int(p_idx),
            "s_pick_idx": int(s_idx),
        }
        if CONFIG["mode"] == "recovery_summary":
            gap = int(s_idx - p_idx)
            row["sp_gap_samples"] = gap
            row["recovery_band"] = gap_band(gap)
        rows.append(row)
    write_csv(output_path, CONFIG["fieldnames"], rows)


def run_continuous_mode() -> None:
    input_dir = Path(CONFIG["input_dir"])
    output_path = Path(CONFIG["output_file"])
    rows = []
    for npz_path in sorted(input_dir.glob("*.npz")):
        stream_id = npz_path.stem
        events = pick_multi_events(load_waveform(npz_path), CONFIG["events_per_stream"])
        for event_order, (p_idx, s_idx) in enumerate(events, start=1):
            rows.append(
                {
                    "stream_id": stream_id,
                    "event_order": event_order,
                    "p_pick_idx": int(p_idx),
                    "s_pick_idx": int(s_idx),
                    "sp_gap_samples": int(s_idx - p_idx),
                }
            )
    rows.sort(key=lambda row: (row["stream_id"], row["event_order"]))
    write_csv(output_path, CONFIG["fieldnames"], rows)


def run_pack_mode() -> None:
    raw_dir = Path(CONFIG["raw_dir"])
    packs = json.loads(Path(CONFIG["packs_manifest"]).read_text())
    output_path = Path(CONFIG["output_file"])

    results = []
    for pack in packs:
        gaps = []
        for file_name in pack["files"]:
            p_idx, s_idx = pick_single_event(load_waveform(raw_dir / file_name))
            gaps.append({"file_name": file_name, "gap": int(s_idx - p_idx)})
        gaps.sort(key=lambda item: (item["gap"], item["file_name"]))
        gap_values = sorted(item["gap"] for item in gaps)
        median_gap = int(np.median(np.asarray(gap_values, dtype=np.int64)))
        winner = gaps[-1]
        results.append(
            {
                "pack_id": pack["pack_id"],
                "largest_gap_file": winner["file_name"],
                "largest_gap_samples": int(winner["gap"]),
                "median_gap_samples": median_gap,
            }
        )
    results.sort(key=lambda item: item["pack_id"])
    output_path.write_text(json.dumps(results, indent=2) + "\n")


def main() -> None:
    mode = CONFIG["mode"]
    if mode in {"single_trace", "recovery_summary"}:
        run_single_trace_mode()
    elif mode == "continuous_events":
        run_continuous_mode()
    elif mode == "pack_summary":
        run_pack_mode()
    else:
        raise ValueError(f"Unsupported mode: {mode}")


if __name__ == "__main__":
    main()
