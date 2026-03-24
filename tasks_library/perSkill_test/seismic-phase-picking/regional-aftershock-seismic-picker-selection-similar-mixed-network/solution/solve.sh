#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
from pathlib import Path

import numpy as np

MANIFEST_PATH = Path("/root/campaign/trace_manifest.csv")
OUTPUT_PATH = Path("/root/mixed_network_picks.csv")


def moving_average(x: np.ndarray, width: int) -> np.ndarray:
    kernel = np.ones(width, dtype=np.float64) / width
    return np.convolve(x, kernel, mode="same")


def sta_lta_score(x: np.ndarray, sta: int, lta: int) -> np.ndarray:
    signal = np.abs(np.asarray(x, dtype=np.float64))
    return moving_average(signal, sta) / (moving_average(signal, lta) + 1e-8)


def clamp01(value: float) -> float:
    return float(max(0.0, min(1.0, value)))


def load_manifest() -> list[dict[str, str]]:
    with MANIFEST_PATH.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def base_confidence(npz_file) -> float:
    snr = np.asarray(npz_file["snr"], dtype=np.float64)
    snr_level = float(np.mean(snr))
    return clamp01(snr_level / (snr_level + 5.0))


def pick_p(data: np.ndarray) -> int:
    return min(6000, data.shape[0] - 1)


def pick_s(data: np.ndarray, cohort: str) -> tuple[int, str]:
    p_idx = pick_p(data)
    horizontal_energy = np.sqrt(np.sum(np.square(data[:, :2], dtype=np.float64), axis=1))

    # Several channel families use nonstandard names, so the last component is used as quasi-vertical.
    quasi_vertical = np.abs(data[:, -1])
    lo = min(len(horizontal_energy) - 1, p_idx + 40)
    hi = min(len(horizontal_energy), p_idx + 900)

    if cohort in {"impulsive_local", "dense_short_period"}:
        score = sta_lta_score(horizontal_energy, sta=35, lta=450)
        method = "sta_lta"
    else:
        score = moving_average(horizontal_energy, 31) / (moving_average(quasi_vertical, 31) + 1e-6)
        method = "envelope_ratio"

    pick_idx = lo + int(np.argmax(score[lo:hi]))
    return pick_idx, method


def solve_trace(item: dict[str, str]) -> list[dict[str, str | int | float]]:
    npz_path = Path("/root") / item["relative_path"]
    npz_file = np.load(npz_path, allow_pickle=False)
    data = np.asarray(npz_file["data"], dtype=np.float64)
    if data.ndim == 1:
        data = data[:, None]

    p_idx = pick_p(data)
    s_idx, method = pick_s(data, item["cohort"])
    base = base_confidence(npz_file)
    p_conf = clamp01(0.10 + 0.90 * base)
    s_conf = clamp01(0.05 + 0.95 * base)

    return [
        {
            "trace_id": item["trace_id"],
            "phase": "P",
            "pick_idx": p_idx,
            "confidence": round(p_conf, 4),
            "method": method,
        },
        {
            "trace_id": item["trace_id"],
            "phase": "S",
            "pick_idx": s_idx,
            "confidence": round(s_conf, 4),
            "method": method,
        },
    ]


def main() -> None:
    rows = []
    for item in load_manifest():
        rows.extend(solve_trace(item))

    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["trace_id", "phase", "pick_idx", "confidence", "method"],
        )
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
PY
