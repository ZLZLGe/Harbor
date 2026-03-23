#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import re
import sys
from pathlib import Path

import pandas as pd

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")


def extract_number(value):
    if pd.isna(value):
        return None
    match = NUMBER_RE.search(str(value))
    return match.group() if match else None


def extract_email(value):
    if pd.isna(value):
        return None
    match = EMAIL_RE.search(str(value))
    return match.group() if match else None

config = json.loads(Path("/root/data/task_config.json").read_text())
cleaned = pd.read_csv(config["input_file"])

for step in config["steps"]:
    strategy = step["strategy"]
    kwargs = step.get("kwargs", {})

    if strategy == "remove_duplicates":
        cleaned = cleaned.drop_duplicates(subset=kwargs.get("subset"))
    elif strategy == "drop_missing":
        cleaned = cleaned.dropna(subset=kwargs.get("columns", []))
    elif strategy == "process_text":
        operation = kwargs.get("operation")
        for column in kwargs.get("columns", []):
            if column not in cleaned.columns:
                continue
            if operation == "extract_numbers":
                cleaned[column] = cleaned[column].apply(extract_number)
            elif operation == "extract_email":
                cleaned[column] = cleaned[column].apply(extract_email)
            elif operation == "clean_whitespace":
                cleaned[column] = cleaned[column].apply(
                    lambda value: value.strip() if isinstance(value, str) else value
                )
            else:
                raise ValueError(f"Unsupported text operation: {operation}")
    elif strategy == "impute_median":
        for column in kwargs.get("columns", []):
            if column not in cleaned.columns:
                continue
            numeric_series = pd.to_numeric(cleaned[column], errors="coerce")
            cleaned[column] = numeric_series.fillna(numeric_series.median())
    elif strategy == "cap_outliers_iqr":
        multiplier = kwargs.get("multiplier", 1.5)
        for column in kwargs.get("columns", []):
            if column not in cleaned.columns:
                continue
            numeric_series = pd.to_numeric(cleaned[column], errors="coerce")
            valid = numeric_series.dropna()
            if valid.empty:
                cleaned[column] = numeric_series
                continue
            q1 = valid.quantile(0.25)
            q3 = valid.quantile(0.75)
            iqr = q3 - q1
            cleaned[column] = numeric_series.clip(
                lower=q1 - multiplier * iqr,
                upper=q3 + multiplier * iqr,
            )
    else:
        raise ValueError(f"Unsupported strategy: {strategy}")

    if "restock_note" in cleaned.columns:
        debug_values = cleaned["restock_note"].astype(object).where(cleaned["restock_note"].notna(), None).tolist()
        print(json.dumps({"strategy": strategy, "restock_note": debug_values}), file=sys.stderr)

for column in config.get("numeric_columns", []):
    if column in cleaned.columns:
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")

for column in config.get("strip_columns", []):
    if column in cleaned.columns:
        cleaned[column] = cleaned[column].apply(lambda value: value.strip() if isinstance(value, str) else value)

if config.get("sort_by"):
    cleaned = cleaned.sort_values(config["sort_by"]).reset_index(drop=True)

output_path = Path(config["output_file"])
output_path.parent.mkdir(parents=True, exist_ok=True)
cleaned.to_csv(output_path, index=False)

summary = {
    "row_count": int(len(cleaned)),
    "columns": cleaned.columns.tolist(),
    "null_counts": {key: int(value) for key, value in cleaned.isna().sum().to_dict().items()},
}
Path(config["summary_file"]).write_text(json.dumps(summary, indent=2))
PY
