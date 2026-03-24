#!/bin/bash
set -euo pipefail

TASK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 - "$TASK_ROOT" <<'PY'
from pathlib import Path
import sys

import numpy as np
import pandas as pd


def resolve_data_path(task_root: Path) -> Path:
    candidates = [
        Path("/root/us_beveridge_monthly.csv"),
        task_root / "environment" / "us_beveridge_monthly.csv",
    ]
    for path in candidates:
        try:
            if path.exists():
                return path
        except PermissionError:
            continue
    raise FileNotFoundError("Could not locate us_beveridge_monthly.csv")


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
    df = pd.read_csv(resolve_data_path(task_root))

    unemployment_cycle = hp_cycle(df["unemployment_rate"], lamb=129600)
    vacancy_cycle = hp_cycle(df["job_openings_rate"], lamb=129600)
    corr = float(np.corrcoef(unemployment_cycle, vacancy_cycle)[0, 1])

    output_candidates = [
        Path("/root/beveridge-cycle-corr.txt"),
        task_root / "beveridge-cycle-corr.txt",
    ]
    for output_path in output_candidates:
        try:
            output_path.write_text(f"{corr:.5f}", encoding="utf-8")
            return
        except OSError:
            continue
    raise OSError("Could not write output file")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
PY
