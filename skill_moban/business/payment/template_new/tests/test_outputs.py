from __future__ import annotations

import json

from common import OUTPUT_ROOT, ROW_FIELDS, build_expected, read_summary, read_worklist, row_matches_expected


def test_required_output_files_exist() -> None:
    assert (OUTPUT_ROOT / "billing_actions.csv").exists(), "Missing /root/output/billing_actions.csv"
    assert (OUTPUT_ROOT / "billing_run_summary.json").exists(), "Missing /root/output/billing_run_summary.json"


def test_billing_action_rows_match_expected() -> None:
    expected = build_expected()
    actual_rows = read_worklist()
    assert len(actual_rows) == len(expected["rows"]), "Unexpected number of billing rows"
    actual_by_id = {row["subscription_id"]: row for row in actual_rows}
    expected_by_id = {row["subscription_id"]: row for row in expected["rows"]}
    assert list(actual_rows[0].keys()) == ROW_FIELDS, "CSV header mismatch"
    assert set(actual_by_id) == set(expected_by_id), "Subscription set mismatch"
    for subscription_id, expected_row in expected_by_id.items():
        actual_row = actual_by_id[subscription_id]
        assert row_matches_expected(actual_row, expected_row), f"{subscription_id} row mismatch"


def test_evidence_fields_are_valid_json_and_auditable() -> None:
    for row in read_worklist():
        payload = json.loads(row["evidence"])
        assert payload["subscription_id"] == row["subscription_id"]
        assert payload["invoice_id"] == row["latest_invoice_id"]
        assert "plan_price_id" in payload
        assert "customer_tax_country" in payload
        assert "metered_price_ids" in payload


def test_summary_matches_recomputed_values() -> None:
    expected = build_expected()
    summary = read_summary()
    assert summary["workspace_id"] == expected["manifest"]["workspace_id"]
    assert summary["run_date"] == expected["manifest"]["run_date"]
    assert summary["totals"] == expected["summary"]["totals"]
    assert summary["action_counts"] == expected["summary"]["action_counts"]
    assert summary["blocked_subscription_ids"] == expected["summary"]["blocked_subscription_ids"]
    assert isinstance(summary["notes"], list) and len(summary["notes"]) >= 2
