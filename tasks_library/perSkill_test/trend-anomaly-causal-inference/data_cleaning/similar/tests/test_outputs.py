import json
from pathlib import Path

import pandas as pd


CONFIG = json.loads(Path("/root/data/task_config.json").read_text())
EXPECTED = json.loads(Path("/root/data/expected.json").read_text())


def test_cleaned_output_exists():
    assert Path(CONFIG["output_file"]).exists(), f"Missing output file: {CONFIG['output_file']}"
    assert Path(CONFIG["summary_file"]).exists(), f"Missing summary file: {CONFIG['summary_file']}"


def test_cleaned_output_quality():
    df = pd.read_csv(CONFIG["output_file"])

    assert len(df) == EXPECTED["row_count"], f"Expected {EXPECTED['row_count']} rows, got {len(df)}"

    for column in EXPECTED.get("required_non_null", []):
        assert df[column].notna().all(), f"Column {column} still contains null values"

    unique_subset = EXPECTED.get("unique_subset")
    if unique_subset:
        assert df.duplicated(subset=unique_subset).sum() == 0, f"Duplicate rows remain on {unique_subset}"

    for column in EXPECTED.get("numeric_columns", []):
        numeric_series = pd.to_numeric(df[column], errors="coerce")
        assert numeric_series.notna().all(), f"Column {column} must be numeric after cleaning"

    for column, max_value in EXPECTED.get("max_values", {}).items():
        assert pd.to_numeric(df[column], errors="coerce").max() <= max_value, f"{column} exceeds {max_value}"

    for column, min_value in EXPECTED.get("min_values", {}).items():
        assert pd.to_numeric(df[column], errors="coerce").min() >= min_value, f"{column} falls below {min_value}"

    for value_check in EXPECTED.get("value_checks", []):
        mask = pd.Series([True] * len(df))
        for key, expected in value_check["match"].items():
            mask &= df[key].astype(str) == str(expected)
        matches = df[mask]
        assert len(matches) == 1, f"Expected one row for match {value_check['match']}, found {len(matches)}"
        observed = str(matches.iloc[0][value_check["column"]])
        assert observed == str(value_check["value"]), (
            f"Unexpected value for {value_check['column']} with match {value_check['match']}: {observed}"
        )
