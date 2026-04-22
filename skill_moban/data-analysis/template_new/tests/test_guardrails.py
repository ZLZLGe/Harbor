from __future__ import annotations

import hashlib
import os
from pathlib import Path


PROTECTED_PATHS = {
    "reference/metric_contract.json": None,
    "subscriptions/account_month_status.csv": None,
    "product/usage_monthly.csv": None,
    "support/tickets.csv": None,
    "orders/invoices.csv": None,
}
DATA_ROOT = Path(os.environ.get("BOARD_DATA_ROOT", "/app/data"))
SERVER_PATH = Path(os.environ.get("BOARD_AUDIT_SERVER_PATH", "/services/board-audit/server.py"))
SERVER_HASH_PATH = Path(os.environ.get("BOARD_AUDIT_SERVER_SHA_PATH", "/opt/board-audit-server.sha256"))
SUMMARY_PATH = Path(os.environ.get("BOARD_OUTPUT_ROOT", "/app/output")) / "executive_summary.md"
DIAGNOSIS_PATH = Path(os.environ.get("BOARD_OUTPUT_ROOT", "/app/output")) / "diagnosis_report.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_hidden_service_unchanged() -> None:
    assert SERVER_HASH_PATH.exists()
    assert sha256(SERVER_PATH) == SERVER_HASH_PATH.read_text(encoding="utf-8").strip()


def test_protected_inputs_look_real_and_unchanged_shape() -> None:
    for raw_path in PROTECTED_PATHS:
        path = DATA_ROOT / raw_path
        assert path.exists(), raw_path
        assert path.stat().st_size > 100, raw_path


def test_outputs_are_not_placeholders() -> None:
    summary = SUMMARY_PATH.read_text(encoding="utf-8").strip().lower()
    diagnosis = DIAGNOSIS_PATH.read_text(encoding="utf-8").strip().lower()
    blocked = {"todo", "placeholder", "n/a", "unknown"}
    assert summary not in blocked
    assert diagnosis not in blocked
