from __future__ import annotations

import csv
import importlib.util
import json
import os
import random
import subprocess
import sys
import time
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

import requests


TASK_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = Path("/app/workspace")
OUT_DIR = WORKSPACE_ROOT / "out"
STATE_DIR = WORKSPACE_ROOT / "state"
GATEWAY_URL = "http://127.0.0.1:8320"
MERCHANTS_PATH = WORKSPACE_ROOT / "data" / "merchants.json"
REFERENCE_LEDGER = WORKSPACE_ROOT / "data" / "reference" / "ledger.jsonl"
DIRTY_LEDGER = WORKSPACE_ROOT / "data" / "incidents" / "dirty_incident_ledger.jsonl"
TWOPLACES = Decimal("0.01")

SCENARIOS = {
    "reference_batch": REFERENCE_LEDGER,
    "dirty_incident_batch": DIRTY_LEDGER,
}


def money(value: Any) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def fmt_money(value: Decimal) -> str:
    return f"{value.quantize(TWOPLACES, rounding=ROUND_HALF_UP):.2f}"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_merchants(path: Path) -> dict[str, dict[str, Any]]:
    return {item["merchant_id"]: item for item in load_json(path)}


def ensure_gateway_running() -> None:
    try:
        requests.get(f"{GATEWAY_URL}/health", timeout=1).raise_for_status()
        return
    except requests.RequestException:
        pass

    env = os.environ.copy()
    env.setdefault("SETTLEMENT_GATEWAY_TOKEN", "settlement-gateway-demo-token")
    subprocess.Popen(
        [sys.executable, "/services/settlement-gateway/server.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
        start_new_session=True,
    )

    for _ in range(40):
        try:
            requests.get(f"{GATEWAY_URL}/health", timeout=1).raise_for_status()
            return
        except requests.RequestException:
            time.sleep(0.25)

    raise RuntimeError("settlement gateway did not start")


def gateway_post(path: str, *, json_payload: dict[str, Any] | None = None, params: dict[str, Any] | None = None) -> requests.Response:
    ensure_gateway_running()
    return requests.post(
        f"{GATEWAY_URL}{path}",
        headers={"X-Settlement-Gateway-Token": "settlement-gateway-demo-token"},
        json=json_payload,
        params=params,
        timeout=10,
    )


def gateway_get(path: str) -> requests.Response:
    ensure_gateway_running()
    return requests.get(f"{GATEWAY_URL}{path}", timeout=10)


def gateway_reset() -> None:
    gateway_post("/api/v1/reset").raise_for_status()


def gateway_audit() -> dict[str, Any]:
    response = gateway_get("/api/v1/audit")
    response.raise_for_status()
    return response.json()


def gateway_integrity() -> dict[str, str]:
    response = gateway_get("/api/v1/integrity")
    response.raise_for_status()
    return response.json()


def clean_workspace() -> None:
    for root in (OUT_DIR, STATE_DIR):
        if not root.exists():
            continue
        for path in root.iterdir():
            if path.is_file():
                path.unlink()


def run_gate() -> subprocess.CompletedProcess[str]:
    clean_workspace()
    gateway_reset()
    return subprocess.run(
        ["make", "-C", str(WORKSPACE_ROOT), "quality-gate"],
        text=True,
        capture_output=True,
        check=False,
    )


def _resolve_batch_id(event: dict[str, Any]) -> str:
    return (event.get("processor_batch_id") or event.get("fallback_batch_id") or "").strip()


def reference_daily_rows(ledger_path: Path, merchants_path: Path) -> list[dict[str, str]]:
    merchants = load_merchants(merchants_path)
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)

    for event in load_jsonl(ledger_path):
        if event["status"] != "posted":
            continue
        key = (event["settlement_date"], event["merchant_id"], event["currency"])
        groups[key].append(event)

    rows: list[dict[str, str]] = []
    for (settlement_date, merchant_id, currency), events in sorted(groups.items()):
        sorted_events = sorted(
            events,
            key=lambda item: (
                item["settlement_date"],
                item["occurred_at"],
                item["event_id"],
            ),
        )
        gross_amount = money("0")
        fee_amount = money("0")
        adjustment_amount = money("0")
        charge_count = 0
        adjustment_count = 0
        batch_id = ""

        for event in sorted_events:
            event_type = event["event_type"]
            fee_amount += money(event["fee_amount"])
            if not batch_id:
                batch_id = _resolve_batch_id(event)
            if event_type == "charge":
                gross_amount += money(event["gross_amount"])
                charge_count += 1
            else:
                adjustment_amount += money(event["adjustment_amount"])
                adjustment_count += 1

        rows.append(
            {
                "report_type": "daily",
                "report_date": settlement_date,
                "merchant_id": merchant_id,
                "merchant_name": merchants[merchant_id]["merchant_name"],
                "currency": currency,
                "processor_batch_id": batch_id,
                "event_count": str(len(sorted_events)),
                "charge_count": str(charge_count),
                "adjustment_count": str(adjustment_count),
                "gross_amount": fmt_money(gross_amount),
                "fee_amount": fmt_money(fee_amount),
                "adjustment_amount": fmt_money(adjustment_amount),
                "net_settlement_amount": fmt_money(gross_amount - fee_amount + adjustment_amount),
            }
        )
    return rows


def reference_monthly_rows(ledger_path: Path, merchants_path: Path) -> list[dict[str, str]]:
    merchants = load_merchants(merchants_path)
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)

    for event in load_jsonl(ledger_path):
        if event["status"] != "posted":
            continue
        key = (event["settlement_date"][:7], event["merchant_id"], event["currency"])
        groups[key].append(event)

    rows: list[dict[str, str]] = []
    for (report_month, merchant_id, currency), events in sorted(groups.items()):
        sorted_events = sorted(
            events,
            key=lambda item: (
                item["settlement_date"],
                item["occurred_at"],
                item["event_id"],
            ),
        )
        gross_amount = money("0")
        fee_amount = money("0")
        adjustment_amount = money("0")
        charge_count = 0
        refund_count = 0
        chargeback_count = 0
        adjustment_count = 0
        batch_ids: list[str] = []
        settlement_dates: list[str] = []

        for event in sorted_events:
            event_type = event["event_type"]
            fee_amount += money(event["fee_amount"])
            settlement_dates.append(event["settlement_date"])
            batch_ids.append(_resolve_batch_id(event))
            if event_type == "charge":
                gross_amount += money(event["gross_amount"])
                charge_count += 1
            else:
                adjustment_amount += money(event["adjustment_amount"])
                adjustment_count += 1
                if event_type == "refund":
                    refund_count += 1
                if event_type == "chargeback":
                    chargeback_count += 1

        rows.append(
            {
                "report_type": "monthly",
                "report_month": report_month,
                "merchant_id": merchant_id,
                "merchant_name": merchants[merchant_id]["merchant_name"],
                "currency": currency,
                "charge_count": str(charge_count),
                "refund_count": str(refund_count),
                "chargeback_count": str(chargeback_count),
                "adjustment_count": str(adjustment_count),
                "gross_amount": fmt_money(gross_amount),
                "fee_amount": fmt_money(fee_amount),
                "adjustment_amount": fmt_money(adjustment_amount),
                "net_settlement_amount": fmt_money(gross_amount - fee_amount + adjustment_amount),
                "first_settlement_date": settlement_dates[0],
                "last_settlement_date": settlement_dates[-1],
                "first_batch_id": batch_ids[0],
                "last_batch_id": batch_ids[-1],
            }
        )
    return rows


def load_exporter_module():
    if str(WORKSPACE_ROOT) not in sys.path:
        sys.path.insert(0, str(WORKSPACE_ROOT))
    path = WORKSPACE_ROOT / "settlement_quality" / "exporter.py"
    spec = importlib.util.spec_from_file_location("solver_exporter", path)
    assert spec is not None and spec.loader is not None, f"unable to load exporter from {path}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_actual_rows(ledger_path: Path, merchants_path: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    module = load_exporter_module()
    return module.build_daily_rows(ledger_path, merchants_path), module.build_monthly_rows(ledger_path, merchants_path)


def build_shuffled_fixture_copy(ledger_path: Path, merchants_path: Path) -> tuple[Path, Path]:
    tmp_root = Path(
        subprocess.check_output(
            [sys.executable, "-c", "import tempfile; print(tempfile.mkdtemp(prefix='settlement-shuffle-'))"],
            text=True,
        ).strip()
    )
    shuffled_ledger = tmp_root / "ledger.jsonl"
    shuffled_merchants = tmp_root / "merchants.json"
    events = load_jsonl(ledger_path)
    rng = random.Random(17)
    rng.shuffle(events)
    shuffled_ledger.write_text(
        "\n".join(json.dumps(event, separators=(",", ":")) for event in events) + "\n",
        encoding="utf-8",
    )
    shuffled_merchants.write_text(merchants_path.read_text(encoding="utf-8"), encoding="utf-8")
    return shuffled_ledger, shuffled_merchants
