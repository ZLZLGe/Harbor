#!/bin/bash
set -e

TASK_DIR="$(cd "$(dirname "$0")/.." && pwd)"
export TASK_DIR

python3 <<'PY'
import json
import os

import numpy as np
import pandas as pd


def locate_input():
    candidates = [
        "/root/monthly_saas_marketing.csv",
        os.path.join(os.environ["TASK_DIR"], "environment", "monthly_saas_marketing.csv"),
        "monthly_saas_marketing.csv",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    raise FileNotFoundError("monthly_saas_marketing.csv not found")


def locate_output():
    return "/root/lead_lag_cycles.json"


def hp_cycle(values, lamb=14400.0):
    y = np.asarray(values, dtype=float)
    n = y.shape[0]
    identity = np.eye(n)
    second_diff = np.diff(identity, n=2, axis=0)
    trend = np.linalg.solve(identity + lamb * (second_diff.T @ second_diff), y)
    return y - trend


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


data = pd.read_csv(locate_input())
window = data[(data["month"] >= "2018-01") & (data["month"] <= "2023-12")].copy()

marketing_cycle = hp_cycle(np.log(window["real_marketing_spend"].astype(float).to_numpy()))
subscriptions_cycle = hp_cycle(np.log(window["subscription_starts"].astype(float).to_numpy()))

lag_to_corr = {lag: aligned_corr(marketing_cycle, subscriptions_cycle, lag) for lag in range(-3, 4)}
best_lag = max(lag_to_corr, key=lag_to_corr.get)

result = {
    "best_lag_months": int(best_lag),
    "correlation": round(lag_to_corr[best_lag], 6),
}

with open(locate_output(), "w", encoding="utf-8") as handle:
    json.dump(result, handle, ensure_ascii=False, indent=2)
    handle.write("\n")
PY
