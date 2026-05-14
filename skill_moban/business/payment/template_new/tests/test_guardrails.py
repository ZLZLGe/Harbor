from __future__ import annotations

import csv
import json
import shutil
import subprocess
from pathlib import Path

from common import DATA_ROOT, INPUT_HASH_PATH, OUTPUT_ROOT, build_expected, clone_data_root, read_worklist, row_matches_expected, run_app


def _current_input_hashes(data_root: Path = DATA_ROOT) -> str:
    return subprocess.check_output(
        f"find {data_root} -type f -print0 | sort -z | xargs -0 sha256sum",
        shell=True,
        text=True,
    ).strip()


def test_input_files_were_not_modified() -> None:
    assert INPUT_HASH_PATH.exists(), "Missing input hash baseline"
    assert _current_input_hashes() == INPUT_HASH_PATH.read_text(encoding="utf-8").strip()


def test_no_extra_top_level_outputs() -> None:
    assert sorted(path.name for path in OUTPUT_ROOT.iterdir() if path.is_file()) == [
        "billing_actions.csv",
        "billing_run_summary.json",
    ]


def test_replaying_main_reproduces_expected_outputs() -> None:
    replay_root = Path("/tmp/payment-replay")
    if replay_root.exists():
        shutil.rmtree(replay_root)
    replay_root.mkdir(parents=True, exist_ok=True)
    rows, summary = run_app(DATA_ROOT, replay_root)
    expected = build_expected()
    assert len(rows) == len(expected["rows"])
    actual_by_id = {row["subscription_id"]: row for row in rows}
    expected_by_id = {row["subscription_id"]: row for row in expected["rows"]}
    assert set(actual_by_id) == set(expected_by_id)
    for subscription_id, expected_row in expected_by_id.items():
        assert row_matches_expected(actual_by_id[subscription_id], expected_row)
    assert summary["totals"] == expected["summary"]["totals"]
    assert summary["action_counts"] == expected["summary"]["action_counts"]
    assert summary["blocked_subscription_ids"] == expected["summary"]["blocked_subscription_ids"]


def test_shadow_run_reacts_to_usage_change() -> None:
    shadow_data, shadow_output = clone_data_root()
    usage_path = shadow_data / "usage_rollups.csv"
    rows = []
    with usage_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row["subscription_id"] == "SUB-1001" and row["price_id"] == "price_api_calls_metered":
                row["usage_quantity"] = str(int(row["usage_quantity"]) + 17)
            rows.append(row)
    with usage_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    worklist, summary = run_app(shadow_data, shadow_output)
    changed_row = {row["subscription_id"]: row for row in worklist}["SUB-1001"]
    assert changed_row["renewal_amount_due"] == "372.36"
    assert changed_row["tax_amount"] == "30.72"
    assert summary["totals"]["total_renewal_amount_due"] == 3842.36


def test_shadow_run_reacts_to_current_cycle_quantity_change() -> None:
    shadow_data, shadow_output = clone_data_root()
    change_path = shadow_data / "change_requests.csv"
    rows = []
    with change_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row["change_request_id"] == "CR-1007-UPSIZE":
                row["target_quantity"] = "16"
            rows.append(row)
    with change_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    worklist, summary = run_app(shadow_data, shadow_output)
    changed_row = {row["subscription_id"]: row for row in worklist}["SUB-1007"]
    assert changed_row["renewal_amount_due"] == "1304.00"
    assert changed_row["adjustment_amount"] == "47.40"
    assert changed_row["tax_amount"] == "256.77"
    assert changed_row["action_bucket"] == "charge_renewal"
    assert summary["totals"]["total_renewal_amount_due"] == 3999.0


def test_shadow_run_prioritizes_pause_over_missing_payment_method() -> None:
    shadow_data, shadow_output = clone_data_root()
    invoice_path = shadow_data / "invoice_snapshot.ndjson"
    rows = []
    with invoice_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row["subscription_id"] == "SUB-1003":
                row["attempt_count"] = 4
                row["due_date"] = "2026-04-10"
            rows.append(row)
    invoice_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    worklist, summary = run_app(shadow_data, shadow_output)
    changed_row = {row["subscription_id"]: row for row in worklist}["SUB-1003"]
    assert changed_row["action_bucket"] == "pause_entitlement"
    assert changed_row["action_reason"] == "collection_exhausted"
    assert "SUB-1003" in summary["blocked_subscription_ids"]


def test_shadow_run_prioritizes_pause_over_retry() -> None:
    shadow_data, shadow_output = clone_data_root()
    invoice_path = shadow_data / "invoice_snapshot.ndjson"
    rows = []
    with invoice_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row["subscription_id"] == "SUB-1002":
                row["attempt_count"] = 4
                row["next_payment_attempt"] = "2026-05-14"
                row["due_date"] = "2026-04-10"
            rows.append(row)
    invoice_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    worklist, summary = run_app(shadow_data, shadow_output)
    changed_row = {row["subscription_id"]: row for row in worklist}["SUB-1002"]
    assert changed_row["action_bucket"] == "pause_entitlement"
    assert changed_row["action_reason"] == "collection_exhausted"
    assert "SUB-1002" in summary["blocked_subscription_ids"]


def test_shadow_run_manual_invoice_with_outstanding_still_routes_manual_invoice() -> None:
    shadow_data, shadow_output = clone_data_root()
    subscription_path = shadow_data / "subscription_snapshot.ndjson"
    invoice_path = shadow_data / "invoice_snapshot.ndjson"

    subscription_rows = []
    with subscription_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["subscription_id"] == "SUB-1006":
                row["collection_method"] = "send_invoice"
            subscription_rows.append(row)
    subscription_path.write_text("".join(json.dumps(row) + "\n" for row in subscription_rows), encoding="utf-8")

    invoice_rows = []
    with invoice_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["subscription_id"] == "SUB-1006":
                row["status"] = "open"
                row["amount_remaining"] = "149.00"
                row["due_date"] = "2026-05-10"
            invoice_rows.append(row)
    invoice_path.write_text("".join(json.dumps(row) + "\n" for row in invoice_rows), encoding="utf-8")

    worklist, summary = run_app(shadow_data, shadow_output)
    changed_row = {row["subscription_id"]: row for row in worklist}["SUB-1006"]
    assert changed_row["action_bucket"] == "send_manual_invoice"
    assert changed_row["action_reason"] == "manual_collection_required"
    assert "SUB-1006" not in summary["blocked_subscription_ids"]


def test_shadow_run_past_retry_date_does_not_stay_in_retry_payment() -> None:
    shadow_data, shadow_output = clone_data_root()
    invoice_path = shadow_data / "invoice_snapshot.ndjson"

    invoice_rows = []
    with invoice_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["subscription_id"] == "SUB-1002":
                row["next_payment_attempt"] = "2026-05-12"
            invoice_rows.append(row)
    invoice_path.write_text("".join(json.dumps(row) + "\n" for row in invoice_rows), encoding="utf-8")

    worklist, _summary = run_app(shadow_data, shadow_output)
    changed_row = {row["subscription_id"]: row for row in worklist}["SUB-1002"]
    assert changed_row["action_bucket"] == "pause_entitlement"
    assert changed_row["action_reason"] == "collection_exhausted"


def test_outputs_do_not_use_placeholder_language() -> None:
    text = (OUTPUT_ROOT / "billing_run_summary.json").read_text(encoding="utf-8").lower()
    assert "todo" not in text
    assert "placeholder" not in text
