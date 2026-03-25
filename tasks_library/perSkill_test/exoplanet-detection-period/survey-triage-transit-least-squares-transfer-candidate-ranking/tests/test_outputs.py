from pathlib import Path

import numpy as np
import pandas as pd
from transitleastsquares import transitleastsquares


OUTPUT_PATH = Path("/root/candidate_ranking.csv")
DATA_DIR = Path("/root/data/survey_targets")
THRESHOLD = 9.0


def preprocess(frame: pd.DataFrame) -> pd.DataFrame:
    good = frame.loc[frame["quality"] == 0, ["time_days", "flux", "flux_err"]].copy()
    flux = good["flux"].to_numpy()
    median_flux = np.median(flux)
    mad = np.median(np.abs(flux - median_flux))
    if mad > 0:
        keep = np.abs(flux - median_flux) <= 5 * 1.4826 * mad
        good = good.loc[keep].copy()
    trend = good["flux"].rolling(window=97, center=True, min_periods=1).median()
    good["flat_flux"] = good["flux"] / trend
    return good.reset_index(drop=True)


def run_tls(frame: pd.DataFrame) -> tuple[float, float]:
    tls = transitleastsquares(
        frame["time_days"].to_numpy(),
        frame["flat_flux"].to_numpy(),
        frame["flux_err"].to_numpy(),
    )
    results = tls.power(
        period_min=1.5,
        period_max=12.0,
        use_threads=1,
        show_progress_bar=False,
        verbose=False,
    )
    return float(results.period), float(results.SDE)


def load_output() -> pd.DataFrame:
    assert OUTPUT_PATH.exists(), "Expected output file /root/candidate_ranking.csv was not created."
    frame = pd.read_csv(OUTPUT_PATH)
    return frame


def build_expected_output() -> pd.DataFrame:
    rows = []
    for csv_path in sorted(DATA_DIR.glob("*.csv")):
        target_id = csv_path.stem
        source = pd.read_csv(csv_path)
        computed_period, computed_sde = run_tls(preprocess(source))
        if computed_sde >= THRESHOLD:
            rows.append(
                {
                    "target_id": target_id,
                    "best_period_days": round(computed_period, 5),
                    "tls_sde": round(computed_sde, 3),
                }
            )

    expected = pd.DataFrame(rows, columns=["target_id", "best_period_days", "tls_sde"])
    if not expected.empty:
        expected = expected.sort_values(
            ["tls_sde", "target_id"], ascending=[False, True], kind="mergesort"
        ).reset_index(drop=True)
    return expected


def test_output_columns_and_candidate_ids():
    frame = load_output()
    expected = build_expected_output()
    assert list(frame.columns) == ["target_id", "best_period_days", "tls_sde"]
    assert set(frame["target_id"]) == set(expected["target_id"])
    assert len(frame) == len(expected)
    assert frame["target_id"].is_unique


def test_rows_are_sorted_and_rounded():
    frame = load_output()
    scores = frame["tls_sde"].astype(float).tolist()
    assert scores == sorted(scores, reverse=True), "Rows must be sorted by descending tls_sde."

    for _, row in frame.iterrows():
        period = float(row["best_period_days"])
        score = float(row["tls_sde"])
        assert round(period, 5) == period, "best_period_days must be rounded to 5 decimal places."
        assert round(score, 3) == score, "tls_sde must be rounded to 3 decimal places."
        assert score >= THRESHOLD, "Every reported target must satisfy the declared tls_sde threshold."


def test_reported_values_match_the_tls_search_results():
    frame = load_output()
    expected = build_expected_output()
    expected_by_target = expected.set_index("target_id").to_dict(orient="index")

    for _, row in frame.iterrows():
        target_id = row["target_id"]
        reported_period = float(row["best_period_days"])
        reported_score = float(row["tls_sde"])
        expected_row = expected_by_target[target_id]
        assert reported_period == expected_row["best_period_days"], (
            f"{target_id} best_period_days must equal the TLS period after rounding to 5 decimals."
        )
        assert reported_score == expected_row["tls_sde"], (
            f"{target_id} tls_sde must equal the TLS SDE after rounding to 3 decimals."
        )
