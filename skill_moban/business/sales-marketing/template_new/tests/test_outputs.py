from __future__ import annotations

from common import (
    FORECAST_FIELDS,
    FORECAST_PATH,
    MEMO_PATH,
    PLAN_FIELDS,
    PLAN_PATH,
    SUMMARY_PATH,
    active_foxtrot_pairs,
    build_reference_lookup,
    compute_plan_cost,
    forecast_lookup,
    load_forecast_rows,
    load_inputs,
    load_plan_rows,
    load_summary,
    parse_float,
    parse_int,
    profile_method_map,
    promo_window_pairs,
    setup_lookup,
    vendor_lookup,
)


def test_required_output_files_exist() -> None:
    assert FORECAST_PATH.exists(), "Missing /app/output/forecast_review.csv"
    assert PLAN_PATH.exists(), "Missing /app/output/replenishment_plan.csv"
    assert SUMMARY_PATH.exists(), "Missing /app/output/planning_summary.json"
    assert MEMO_PATH.exists(), "Missing /app/output/planner_memo.md"


def test_forecast_contract_and_coverage() -> None:
    inputs = load_inputs()
    setup_by_pair = setup_lookup(inputs)
    method_by_profile = profile_method_map(inputs)
    actual = load_forecast_rows()

    expected_pairs = set(setup_by_pair)
    expected_row_count = len(expected_pairs) * len(inputs["plan_weeks"])
    assert len(actual) == expected_row_count, "Unexpected number of forecast rows"

    seen_keys = set()
    for row in actual:
        assert list(row.keys()) == FORECAST_FIELDS
        pair_key = (row["store_id"], row["sku_id"])
        assert pair_key in expected_pairs, f"Unexpected forecast pair: {pair_key}"
        expected_method = method_by_profile[setup_by_pair[pair_key]["demand_profile"]]
        assert row["forecast_method"] == expected_method, f"Forecast method mismatch for {pair_key}"
        assert abs(parse_float(row["baseline_units"]) + parse_float(row["promo_lift_units"]) - parse_float(row["final_forecast_units"])) <= 0.02
        seen_keys.add((row["store_id"], row["sku_id"], row["week_start"]))

    assert len(seen_keys) == expected_row_count, "Each store/SKU/week combination must appear once"


def test_forecast_keeps_planning_shape_for_key_profiles() -> None:
    actual = forecast_lookup(load_forecast_rows())
    reference = build_reference_lookup()

    central_alpha = actual[("CENTRAL", "SKU-ALPHA", "2025-04-07")]
    ref_central_alpha = reference[("CENTRAL", "SKU-ALPHA", "2025-04-07")]
    assert abs(parse_float(central_alpha["service_level"]) - parse_float(ref_central_alpha["service_level"])) < 1e-6
    assert parse_float(central_alpha["reorder_point_units"]) > parse_float(central_alpha["final_forecast_units"])

    south_bravo_promo = actual[("SOUTH", "SKU-BRAVO", "2025-04-21")]
    south_bravo_dip = actual[("SOUTH", "SKU-BRAVO", "2025-05-05")]
    assert parse_float(south_bravo_promo["final_forecast_units"]) > parse_float(south_bravo_promo["baseline_units"])
    assert parse_float(south_bravo_dip["final_forecast_units"]) < parse_float(south_bravo_dip["baseline_units"])

    north_foxtrot = actual[("NORTH", "SKU-FOXTROT", "2025-04-07")]
    ref_north_foxtrot = reference[("NORTH", "SKU-FOXTROT", "2025-04-07")]
    assert north_foxtrot["forecast_method"] == ref_north_foxtrot["forecast_method"]
    assert parse_float(north_foxtrot["promo_lift_units"]) > 0
    assert abs(parse_float(north_foxtrot["baseline_units"]) - parse_float(ref_north_foxtrot["baseline_units"])) <= 2.0


def test_replenishment_plan_reflects_priority_tradeoffs() -> None:
    inputs = load_inputs()
    vendor_by_sku = vendor_lookup(inputs)
    promo_pairs = promo_window_pairs(inputs)
    foxtrot_pairs = active_foxtrot_pairs(inputs)
    budget_limit = float(inputs["policy"]["budget"]["limit"])
    max_order_lines = int(inputs["policy"]["review_capacity"]["max_order_lines"])

    actual = load_plan_rows()
    assert 1 <= len(actual) <= max_order_lines, "Plan should stay inside the review-capacity cap"

    promo_orders = 0
    foxtrot_orders = 0
    ordered_pairs = set()
    for row in actual:
        assert list(row.keys()) == PLAN_FIELDS
        sku = row["sku_id"]
        vendor = vendor_by_sku[sku]
        qty = parse_int(row["recommended_order_qty"])
        assert qty > 0
        assert qty >= int(vendor["moq_units"])
        assert qty % int(vendor["case_pack_units"]) == 0
        assert row["order_week_start"] == "2025-04-07", "Current-cycle orders should be placed in the first planning week"

        pair_key = (row["store_id"], row["sku_id"])
        ordered_pairs.add(pair_key)
        if pair_key in promo_pairs and sku == "SKU-BRAVO":
            promo_orders += 1
        if pair_key in foxtrot_pairs:
            foxtrot_orders += 1

    assert promo_orders >= 2, "Near-term promo lines should be protected in the current cycle"
    assert foxtrot_orders >= 1, "At least one active launch line should receive protection in the capped plan"
    planned_cost = compute_plan_cost(actual, inputs)
    assert planned_cost <= budget_limit + 1e-6
    assert planned_cost >= 9400.0, "A strong current-cycle plan should use most of the available budget once promo and launch lines are funded"
    assert ("NORTH", "SKU-DELTA") not in ordered_pairs, "Do not spend the final review slot on a low-tier filler line"
    assert any(token in row["decision_reason"].lower() for row in actual for token in ("promo", "launch", "priority")), (
        "Decision reasons should make the planning tradeoff visible"
    )


def test_summary_and_memo_close_the_loop() -> None:
    inputs = load_inputs()
    summary = load_summary()
    plan_rows = load_plan_rows()
    forecast_rows = load_forecast_rows()
    memo = MEMO_PATH.read_text(encoding="utf-8")

    assert summary["planning_window"]["start_week"] == inputs["manifest"]["planning_window"]["start_week"]
    assert summary["planning_window"]["end_week"] == inputs["manifest"]["planning_window"]["end_week"]
    assert summary["totals"]["forecast_rows"] == len(forecast_rows)
    assert summary["totals"]["planned_orders"] == len(plan_rows)
    assert summary["totals"]["sku_store_pairs"] == len(inputs["setup"])
    assert summary["budget_check"]["within_budget"] is True
    assert summary["budget_check"]["planned_cost"] <= float(inputs["policy"]["budget"]["limit"]) + 1e-6

    exception_codes = {(row["store_id"], row["sku_id"], row["exception_code"]) for row in summary["exceptions"]}
    assert ("NORTH", "SKU-FOXTROT", "analog_based_forecast") in exception_codes
    assert ("CENTRAL", "SKU-FOXTROT", "analog_based_forecast") in exception_codes
    assert ("SOUTH", "SKU-FOXTROT", "analog_based_forecast") in exception_codes
    assert ("SOUTH", "SKU-DELTA", "status_block") in exception_codes
    assert ("SOUTH", "SKU-FOXTROT", "status_block") in exception_codes
    assert any(code == "budget_hold" for _, _, code in exception_codes), "Budget-held lines must stay visible"

    risk_pairs = {(row["store_id"], row["sku_id"]) for row in summary["service_risk_items"]}
    assert ("SOUTH", "SKU-DELTA") in risk_pairs
    assert ("SOUTH", "SKU-FOXTROT") in risk_pairs
    assert isinstance(summary["notes"], list) and len(summary["notes"]) >= 3
    assert summary["planning_window"]["start_week"] in memo
    assert summary["planning_window"]["end_week"] in memo
    assert str(summary["totals"]["planned_orders"]) in memo
    assert str(summary["totals"]["total_recommended_units"]) in memo
    assert "SKU-FOXTROT" in memo
    assert "budget" in memo.lower()
    assert "promo" in memo.lower() or "launch" in memo.lower()
