import json
import math
import os
import re

import numpy as np
import pandas as pd


TOLERANCE = 5e-6


def hp_cycle(values, lamb=14400.0):
    y = np.asarray(values, dtype=float)
    n = y.shape[0]
    identity = np.eye(n)
    second_diff = np.diff(identity, n=2, axis=0)
    trend = np.linalg.solve(identity + lamb * (second_diff.T @ second_diff), y)
    return y - trend


def locate_output():
    path = "/root/lead_lag_cycles.json"
    return path if os.path.exists(path) else None


def locate_input():
    candidates = [
        "/root/monthly_saas_marketing.csv",
        os.path.join(os.getcwd(), "environment", "monthly_saas_marketing.csv"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    raise FileNotFoundError("monthly_saas_marketing.csv not found")


def aligned_corr(marketing_cycle, subscriptions_cycle, lag):
    if lag > 0:
        x = marketing_cycle[:-lag]
        y = subscriptions_cycle[lag:]
    elif lag < 0:
        x = marketing_cycle[-lag:]
        y = subscriptions_cycle[:lag]
    else:
        x = marketing_cycle
        y = subscriptions_cycle
    return float(np.corrcoef(x, y)[0, 1])


def expected_result():
    data = pd.read_csv(locate_input())
    window = data[(data["month"] >= "2018-01") & (data["month"] <= "2023-12")].copy()

    marketing_cycle = hp_cycle(np.log(window["real_marketing_spend"].astype(float).to_numpy()))
    subscriptions_cycle = hp_cycle(np.log(window["subscription_starts"].astype(float).to_numpy()))

    lag_to_corr = {lag: aligned_corr(marketing_cycle, subscriptions_cycle, lag) for lag in range(-3, 4)}
    best_lag = max(lag_to_corr, key=lag_to_corr.get)
    return {
        "best_lag_months": best_lag,
        "correlation": lag_to_corr[best_lag],
    }


def test_output_exists():
    assert locate_output() is not None, "Missing lead_lag_cycles.json"


def test_json_schema_and_ranges():
    output = locate_output()
    if output is None:
        return

    with open(output, encoding="utf-8") as handle:
        payload = json.load(handle)

    assert set(payload.keys()) == {"best_lag_months", "correlation"}
    assert isinstance(payload["best_lag_months"], int)
    assert -3 <= payload["best_lag_months"] <= 3
    assert isinstance(payload["correlation"], (int, float))
    assert -1.0 <= float(payload["correlation"]) <= 1.0


def test_best_lag_and_correlation():
    output = locate_output()
    if output is None:
        return

    with open(output, encoding="utf-8") as handle:
        payload = json.load(handle)

    expected = expected_result()

    assert payload["best_lag_months"] == expected["best_lag_months"]
    assert math.isclose(
        float(payload["correlation"]),
        expected["correlation"],
        abs_tol=TOLERANCE,
    )


def test_correlation_is_written_with_six_decimals():
    output = locate_output()
    if output is None:
        return

    with open(output, encoding="utf-8") as handle:
        text = handle.read()

    assert re.search(r'"correlation"\s*:\s*-?\d+\.\d{6}\b', text)
