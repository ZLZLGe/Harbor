#!/bin/bash
set -e

python3 <<'PY'
import os
from pathlib import Path

import pandas as pd
from statsmodels.tsa.filters.hp_filter import hpfilter


def resolve_input_path() -> Path:
    candidates = [
        Path("/root/fertility_inputs.csv"),
        Path.cwd().parent / "environment" / "fertility_inputs.csv",
        Path.cwd() / "environment" / "fertility_inputs.csv",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError("Could not locate fertility_inputs.csv")


def resolve_output_path() -> Path:
    root_dir = Path("/root")
    if root_dir.exists() and os.access(root_dir, os.W_OK):
        return root_dir / "fertility-cycle-trough.csv"
    return Path.cwd() / "fertility-cycle-trough.csv"


df = pd.read_csv(resolve_input_path()).sort_values("year").reset_index(drop=True)
df["general_fertility_rate"] = df["births"] / df["women_15_44"] * 1000.0

cycle, _ = hpfilter(df["general_fertility_rate"], lamb=100)
trough_idx = cycle.idxmin()

result = pd.DataFrame(
    [
        {
            "year": int(df.loc[trough_idx, "year"]),
            "cycle_gap": round(float(cycle.loc[trough_idx]), 5),
        }
    ]
)
result.to_csv(resolve_output_path(), index=False)
PY
