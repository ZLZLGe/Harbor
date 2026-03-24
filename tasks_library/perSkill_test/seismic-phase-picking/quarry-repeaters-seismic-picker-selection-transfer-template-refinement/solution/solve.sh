#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
from pathlib import Path

import numpy as np


ROOT = Path("/root/repeaters")
OUTPUT = Path("/root/repeater_template_matches.csv")
MATCH_THRESHOLD = 0.25
MAX_LAG = 90


def load_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_waveform(path: Path) -> np.ndarray:
    return np.load(path, allow_pickle=False)["data"].astype(np.float64)


def normalize(segment: np.ndarray) -> np.ndarray:
    centered = segment - np.mean(segment, axis=0, keepdims=True)
    scale = np.std(centered, axis=0, keepdims=True)
    scale[scale < 1e-6] = 1.0
    return centered / scale


def best_alignment(template_data: np.ndarray, candidate_data: np.ndarray, p_idx: int, s_idx: int) -> tuple[float, int]:
    lo = max(0, p_idx - 260)
    hi = min(len(template_data), s_idx + 420)
    template_segment = normalize(template_data[lo:hi])

    best_score = -1.0
    best_lag = 0
    for lag in range(-MAX_LAG, MAX_LAG + 1):
        candidate_lo = lo + lag
        candidate_hi = hi + lag
        if candidate_lo < 0 or candidate_hi > len(candidate_data):
            continue
        candidate_segment = normalize(candidate_data[candidate_lo:candidate_hi])
        score = float(np.mean(template_segment * candidate_segment))
        if score > best_score:
            best_score = score
            best_lag = lag

    return best_score, best_lag


templates = load_manifest(ROOT / "template_manifest.csv")
candidates = load_manifest(ROOT / "candidate_manifest.csv")

template_payloads = []
for template in templates:
    template_payloads.append(
        {
            "template_id": template["template_id"],
            "p_idx": int(template["p_idx"]),
            "s_idx": int(template["s_idx"]),
            "data": load_waveform(ROOT / template["relative_path"].replace("repeaters/", "", 1)),
        }
    )

rows = []
for candidate in candidates:
    file_name = candidate["file_name"]
    candidate_data = load_waveform(ROOT / candidate["relative_path"].replace("repeaters/", "", 1))

    best_template = None
    best_score = -1.0
    best_lag = 0
    for template in template_payloads:
        score, lag = best_alignment(template["data"], candidate_data, template["p_idx"], template["s_idx"])
        if score > best_score:
            best_template = template
            best_score = score
            best_lag = lag

    if best_template is None or best_score < MATCH_THRESHOLD:
        continue

    score_value = round(best_score, 3)
    p_idx = best_template["p_idx"] + best_lag
    s_idx = best_template["s_idx"] + best_lag

    rows.append(
        {
            "template_id": best_template["template_id"],
            "file_name": file_name,
            "phase": "P",
            "pick_idx": p_idx,
            "score": score_value,
        }
    )
    rows.append(
        {
            "template_id": best_template["template_id"],
            "file_name": file_name,
            "phase": "S",
            "pick_idx": s_idx,
            "score": score_value,
        }
    )

rows.sort(key=lambda row: (row["file_name"], 0 if row["phase"] == "P" else 1))

with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=["template_id", "file_name", "phase", "pick_idx", "score"])
    writer.writeheader()
    writer.writerows(rows)
PY
