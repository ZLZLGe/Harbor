from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import tempfile
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import yaml


DATA_ROOT = Path(os.environ.get("TASK_DATA_ROOT", "/root/data"))
OUTPUT_ROOT = Path(os.environ.get("TASK_OUTPUT_ROOT", "/root/output"))
APP_MAIN = Path(os.environ.get("TASK_APP_MAIN", "/root/app/main.py"))
INPUT_HASH_PATH = Path(os.environ.get("TASK_INPUT_HASH_PATH", "/opt/payment-input.sha256"))

ROW_FIELDS = [
    "subscription_id",
    "customer_id",
    "currency",
    "current_status",
    "collection_method",
    "latest_invoice_id",
    "renewal_amount_due",
    "adjustment_amount",
    "tax_amount",
    "outstanding_amount",
    "action_bucket",
    "action_reason",
    "next_step",
    "evidence",
]

TWOPLACES = Decimal("0.01")


def money(value) -> Decimal:
    return Decimal(str(value))


def q(value: Decimal) -> Decimal:
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_ndjson(path: Path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def load_csv(path: Path):
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_policy() -> dict:
    return yaml.safe_load((DATA_ROOT / "billing_policy.yaml").read_text(encoding="utf-8"))


def read_worklist(path: Path = OUTPUT_ROOT / "billing_actions.csv") -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_summary(path: Path = OUTPUT_ROOT / "billing_run_summary.json") -> dict:
    return load_json(path)


def evidence_matches_expected(actual_json: str, expected_json: str) -> bool:
    actual = json.loads(actual_json)
    expected = json.loads(expected_json)
    for key, value in expected.items():
        if actual.get(key) != value:
            return False
    return True


def row_matches_expected(actual_row: dict, expected_row: dict) -> bool:
    for field in ROW_FIELDS:
        if field == "next_step":
            if not (isinstance(actual_row[field], str) and actual_row[field].strip()):
                return False
            continue
        if field == "evidence":
            if not evidence_matches_expected(actual_row[field], expected_row[field]):
                return False
            continue
        if actual_row[field] != expected_row[field]:
            return False
    return True


def recurring_amount(price: dict, quantity: int) -> Decimal:
    return money(price["unit_amount_decimal"]) * Decimal(quantity)


def build_expected(data_root: Path = DATA_ROOT) -> dict:
    manifest = load_json(data_root / "billing_manifest.json")
    catalog = load_json(data_root / "plan_catalog_seed.json")
    subscriptions = {row["subscription_id"]: row for row in load_ndjson(data_root / "subscription_snapshot.ndjson")}
    invoices = {row["subscription_id"]: row for row in load_ndjson(data_root / "invoice_snapshot.ndjson")}
    changes = load_csv(data_root / "change_requests.csv")
    usage = load_csv(data_root / "usage_rollups.csv")
    policy = yaml.safe_load((data_root / "billing_policy.yaml").read_text(encoding="utf-8"))

    prices_by_id = {row["id"]: row for row in catalog["prices"]}
    changes_by_sub: dict[str, list[dict]] = {}
    for row in changes:
        changes_by_sub.setdefault(row["subscription_id"], []).append(row)
    usage_by_sub: dict[str, list[dict]] = {}
    for row in usage:
        usage_by_sub.setdefault(row["subscription_id"], []).append(row)

    run_date = parse_date(manifest["run_date"])
    rows = []
    action_counts = {
        "charge_renewal": 0,
        "send_manual_invoice": 0,
        "retry_payment": 0,
        "collect_payment_method": 0,
        "pause_entitlement": 0,
        "monitor": 0,
    }
    blocked_ids = []

    for subscription_id in manifest["batch_scope"]["subscription_ids"]:
        subscription = subscriptions[subscription_id]
        invoice = invoices[subscription_id]
        applicable_change = None
        for row in changes_by_sub.get(subscription_id, []):
            if row["status"] != "approved":
                continue
            if parse_date(row["effective_date"]) <= parse_date(subscription["renewal_date"]):
                applicable_change = row

        target_price_id = subscription["plan_price_id"]
        target_plan_id = subscription["plan_id"]
        target_quantity = int(subscription["quantity"])
        if applicable_change:
            target_price_id = applicable_change["target_price_id"]
            target_plan_id = applicable_change["target_plan_id"]
            target_quantity = int(applicable_change["target_quantity"])

        licensed_total = recurring_amount(prices_by_id[target_price_id], target_quantity)
        usage_total = Decimal("0")
        for row in usage_by_sub.get(subscription_id, []):
            usage_total += money(prices_by_id[row["price_id"]]["unit_amount_decimal"]) * money(row["usage_quantity"])
        renewal_amount_due = q(licensed_total + usage_total)

        adjustment_amount = Decimal("0")
        if applicable_change and applicable_change["apply_timing"] == "current_cycle":
            start = parse_date(subscription["current_period_start"])
            end = parse_date(subscription["current_period_end"])
            effective = parse_date(applicable_change["effective_date"])
            old_amount = recurring_amount(prices_by_id[subscription["plan_price_id"]], int(subscription["quantity"]))
            new_amount = recurring_amount(prices_by_id[applicable_change["target_price_id"]], int(applicable_change["target_quantity"]))
            total_days = max((end - start).days, 1)
            remaining_days = max((end - effective).days, 0)
            adjustment_amount = q((new_amount - old_amount) * Decimal(remaining_days) / Decimal(total_days))

        taxable_subtotal = renewal_amount_due + adjustment_amount
        if taxable_subtotal < 0:
            taxable_subtotal = Decimal("0")
        tax_amount = q(taxable_subtotal * money(policy["tax_rates"][subscription["customer_tax_country"]]))
        outstanding_amount = q(money(invoice["amount_remaining"]))

        renewal_due = parse_date(subscription["renewal_date"]) <= run_date
        if subscription["collection_method"] == "send_invoice" and (renewal_due or outstanding_amount > 0):
            action_bucket, action_reason = "send_manual_invoice", "manual_collection_required"
        elif outstanding_amount > 0 and subscription["collection_method"] == "charge_automatically":
            due_days = max((run_date - parse_date(invoice["due_date"])).days, 0)
            if (
                int(invoice["attempt_count"]) >= int(policy["collection_exhausted"]["pause_after_attempt_count"])
                or due_days >= int(policy["collection_exhausted"]["pause_after_days_past_due"])
            ):
                action_bucket, action_reason = "pause_entitlement", "collection_exhausted"
            elif subscription["default_payment_method_status"] != "usable":
                action_bucket, action_reason = "collect_payment_method", "payment_method_missing"
            elif (
                invoice["next_payment_attempt"]
                and int(invoice["attempt_count"]) > 0
                and int(invoice["attempt_count"]) <= int(policy["retry_rules"]["max_attempts"])
                and parse_date(invoice["next_payment_attempt"]) >= run_date
            ):
                action_bucket, action_reason = "retry_payment", "retry_window_open"
            else:
                action_bucket, action_reason = "pause_entitlement", "collection_exhausted"
        elif not renewal_due:
            action_bucket, action_reason = "monitor", "upcoming_only"
        else:
            action_bucket, action_reason = "charge_renewal", "renewal_ready"

        action_counts[action_bucket] += 1
        if action_bucket in set(policy["blocked_action_buckets"]):
            blocked_ids.append(subscription_id)

        evidence = {
            "subscription_id": subscription_id,
            "invoice_id": invoice["invoice_id"],
            "plan_price_id": target_price_id,
            "metered_price_ids": subscription["metered_price_ids"],
            "applied_change_request_id": applicable_change["change_request_id"] if applicable_change else None,
            "customer_tax_country": subscription["customer_tax_country"],
        }
        rows.append(
            {
                "subscription_id": subscription_id,
                "customer_id": subscription["customer_id"],
                "currency": subscription["currency"],
                "current_status": subscription["current_status"],
                "collection_method": subscription["collection_method"],
                "latest_invoice_id": invoice["invoice_id"],
                "renewal_amount_due": f"{renewal_amount_due:.2f}",
                "adjustment_amount": f"{adjustment_amount:.2f}",
                "tax_amount": f"{tax_amount:.2f}",
                "outstanding_amount": f"{outstanding_amount:.2f}",
                "action_bucket": action_bucket,
                "action_reason": action_reason,
                "next_step": policy["next_steps"][action_bucket],
                "evidence": json.dumps(evidence, sort_keys=True),
            }
        )

    summary = {
        "workspace_id": manifest["workspace_id"],
        "run_date": manifest["run_date"],
        "totals": {
            "subscriptions_reviewed": len(rows),
            "subscriptions_needing_action": sum(1 for row in rows if row["action_bucket"] != "monitor"),
            "total_renewal_amount_due": round(sum(float(row["renewal_amount_due"]) for row in rows), 2),
            "total_outstanding_amount": round(sum(float(row["outstanding_amount"]) for row in rows), 2),
        },
        "action_counts": action_counts,
        "blocked_subscription_ids": sorted(blocked_ids),
    }

    return {"manifest": manifest, "rows": rows, "summary": summary}


def run_app(data_root: Path, output_root: Path) -> tuple[list[dict], dict]:
    env = os.environ.copy()
    env["TASK_DATA_ROOT"] = str(data_root)
    env["TASK_OUTPUT_ROOT"] = str(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["python3", str(APP_MAIN), "--data-root", str(data_root), "--output-root", str(output_root)],
        check=True,
        env=env,
        capture_output=True,
        text=True,
    )
    return read_worklist(output_root / "billing_actions.csv"), read_summary(output_root / "billing_run_summary.json")


def clone_data_root() -> tuple[Path, Path]:
    temp_dir = Path(tempfile.mkdtemp(prefix="payment-shadow-"))
    shadow_data = temp_dir / "data"
    shadow_output = temp_dir / "out"
    shutil.copytree(DATA_ROOT, shadow_data)
    shadow_output.mkdir(parents=True, exist_ok=True)
    return shadow_data, shadow_output
