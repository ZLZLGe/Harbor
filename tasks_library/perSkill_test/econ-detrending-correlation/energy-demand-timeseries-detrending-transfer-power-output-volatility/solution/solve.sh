#!/bin/bash
set -euo pipefail

TASK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 - "$TASK_ROOT" <<'PY'
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd


OUTPUT_NAME = "power-output-cycle-volatility.json"
DATA_NAME = "us_power_output_monthly.jsonl"
MONTHLY_LAMBDA = 129600


def resolve_data_path(task_root: Path) -> Path:
    candidates = [
        Path("/root") / DATA_NAME,
        task_root / "environment" / DATA_NAME,
    ]
    for path in candidates:
        try:
            if path.exists():
                return path
        except PermissionError:
            continue
    raise FileNotFoundError(f"Could not locate {DATA_NAME}")


def resolve_output_path(task_root: Path) -> Path:
    candidates = [
        Path("/root") / OUTPUT_NAME,
        task_root / OUTPUT_NAME,
    ]
    for path in candidates:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if os.access(path.parent, os.W_OK):
                return path
        except OSError:
            continue
    raise OSError(f"Could not resolve a writable path for {OUTPUT_NAME}")


def hp_cycle(values: pd.Series | np.ndarray, lamb: float) -> np.ndarray:
    y = np.asarray(values, dtype=float)
    n = y.shape[0]
    identity = np.eye(n)
    second_diff = np.zeros((n - 2, n))
    idx = np.arange(n - 2)
    second_diff[idx, idx] = 1.0
    second_diff[idx, idx + 1] = -2.0
    second_diff[idx, idx + 2] = 1.0
    trend = np.linalg.solve(identity + lamb * (second_diff.T @ second_diff), y)
    return y - trend


def main(task_root: Path) -> None:
    df = pd.read_json(resolve_data_path(task_root), lines=True)

    output_cycle = hp_cycle(np.log(df["commercial_power_gwh"]), MONTHLY_LAMBDA)
    production_cycle = hp_cycle(np.log(df["industrial_production_index"]), MONTHLY_LAMBDA)

    commercial_power_cycle_std = float(np.std(output_cycle, ddof=1))
    industrial_production_cycle_std = float(np.std(production_cycle, ddof=1))
    power_to_output_volatility_ratio = commercial_power_cycle_std / industrial_production_cycle_std

    result = {
        "commercial_power_cycle_std": round(commercial_power_cycle_std, 5),
        "industrial_production_cycle_std": round(industrial_production_cycle_std, 5),
        "power_to_output_volatility_ratio": round(power_to_output_volatility_ratio, 5),
    }

    output_path = resolve_output_path(task_root)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
PY
