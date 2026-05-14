from __future__ import annotations

import os
import subprocess
from pathlib import Path

from common import (
    FORECAST_PATH,
    PLAN_PATH,
    SUMMARY_PATH,
    active_foxtrot_pairs,
    compute_plan_cost,
    load_inputs,
    load_plan_rows,
    load_summary,
    parse_int,
)

DATA_ROOT = Path(os.environ.get("TASK_DATA_ROOT", "/app/data"))
HASH_PATH = Path(os.environ.get("TASK_HASH_PATH", "/opt/task-input.sha256"))


def test_input_bundle_was_not_modified() -> None:
    current = subprocess.check_output(
        f"find {DATA_ROOT} -type f -print0 | sort -z | xargs -0 sha256sum",
        shell=True,
        text=True,
    )
    expected = HASH_PATH.read_text(encoding="utf-8")
    assert current == expected, "Input data under /app/data was modified"


def test_blocked_and_inactive_pairs_never_receive_orders() -> None:
    rows = load_plan_rows()
    blocked_pairs = {("SOUTH", "SKU-DELTA"), ("SOUTH", "SKU-FOXTROT")}
    for row in rows:
        assert (row["store_id"], row["sku_id"]) not in blocked_pairs, "Blocked or inactive pairs must not receive planned orders"


def test_plan_stays_focused_on_promo_and_launch_tradeoffs() -> None:
    rows = load_plan_rows()
    active_foxtrot = active_foxtrot_pairs(load_inputs())
    ordered_pairs = {(row["store_id"], row["sku_id"]) for row in rows}

    assert ordered_pairs & active_foxtrot, "A capped current-cycle plan should still protect at least one active launch line"
    assert len(rows) <= 5, "Do not spend review capacity on low-priority filler lines"
    assert {("NORTH", "SKU-ALPHA"), ("NORTH", "SKU-DELTA")}.issubset(ordered_pairs) is False, (
        "Do not crowd out launch protection with both NORTH fallback lines"
    )


def test_budget_and_exception_visibility_remain_consistent() -> None:
    inputs = load_inputs()
    summary = load_summary()
    rows = load_plan_rows()

    assert compute_plan_cost(rows, inputs) <= float(inputs["policy"]["budget"]["limit"]) + 1e-6
    assert summary["budget_check"]["within_budget"] is True
    assert summary["budget_check"]["planned_cost"] <= float(inputs["policy"]["budget"]["limit"]) + 1e-6

    codes = {(row["store_id"], row["sku_id"], row["exception_code"]) for row in summary["exceptions"]}
    assert any(code == "budget_hold" for _, _, code in codes), "Budget-held candidates must remain visible in summary exceptions"


def test_forecast_summary_plan_files_all_exist_together() -> None:
    assert FORECAST_PATH.exists()
    assert PLAN_PATH.exists()
    assert SUMMARY_PATH.exists()
