from __future__ import annotations

import re
from pathlib import Path

from conftest import (
    MERCHANTS_PATH,
    TASK_ROOT,
    build_actual_rows,
    build_shuffled_fixture_copy,
    gateway_integrity,
    reference_daily_rows,
    reference_monthly_rows,
    run_gate,
)


EXPECTED_SERVER_SHA256 = "6dd6c68b655a2e9fb3c058dcd5ce4f803cfc689854eedb111251a3dbf0a67aaf"
EXPECTED_DATA_SHA256 = "d0eb221840b88ec489b0c78ddd20a8f726970b81a796e67af08a2345b1a88a44"


def test_hidden_gateway_and_frozen_data_unchanged() -> None:
    integrity = gateway_integrity()
    assert integrity["server_sha256"] == EXPECTED_SERVER_SHA256
    assert integrity["data_sha256"] == EXPECTED_DATA_SHA256


def test_shuffled_input_order_does_not_change_export_behavior() -> None:
    shuffled_ledger, shuffled_merchants = build_shuffled_fixture_copy(
        Path("/app/workspace/data/reference/ledger.jsonl"),
        MERCHANTS_PATH,
    )
    actual_daily, actual_monthly = build_actual_rows(shuffled_ledger, shuffled_merchants)

    assert actual_daily == reference_daily_rows(shuffled_ledger, shuffled_merchants)
    assert actual_monthly == reference_monthly_rows(shuffled_ledger, shuffled_merchants)


def test_alternate_fixture_generalizes() -> None:
    alt_root = TASK_ROOT / "tests" / "fixtures_alt"
    alt_ledger = alt_root / "ledger.jsonl"
    alt_merchants = alt_root / "merchants.json"
    actual_daily, actual_monthly = build_actual_rows(alt_ledger, alt_merchants)

    assert actual_daily == reference_daily_rows(alt_ledger, alt_merchants)
    assert actual_monthly == reference_monthly_rows(alt_ledger, alt_merchants)

    harbor_monthly = next(row for row in actual_monthly if row["merchant_id"] == "m_harbor")
    assert harbor_monthly["refund_count"] == "1"
    assert harbor_monthly["chargeback_count"] == "1"
    assert harbor_monthly["first_batch_id"] == "stl-20260601-harbor"


def test_quality_assets_are_substantive_and_not_placeholders() -> None:
    result = run_gate()
    assert result.returncode == 0, result.stderr or result.stdout

    quality_files = {
        "QUALITY.md": [("acceptance", "formal scenarios", "release invariants"), "incident", "gateway", "dirty"],
        "RUN_CODE_REVIEW.md": ["review", ("risk", "风险", "regression", "回归"), ("evidence", "证据", "依据", "阻断")],
        "RUN_INTEGRATION_TESTS.md": ["gateway", "reference_batch", "dirty_incident_batch"],
        "RUN_SPEC_AUDIT.md": [
            "spec",
            "contract",
            "incident",
            ("spec summary", "规格摘要"),
            ("incident replay", "事故回放"),
            ("gateway contract diff", "网关契约差异", "contract diff"),
            (
                "rerun audit",
                "重跑审计",
                "probe commands",
                "optional probe commands",
                "probe rerun",
                "rerun probes",
                "replay commands",
                "probe_spec_summary.py",
                "probe_incident_replay.py",
                "probe_gateway_contracts.py",
            ),
        ],
        "test_functional.py": [
            ("dirty_incident_batch", "dirty_ledger", "dirty incident"),
            ("reference_batch", "reference_ledger", "reference"),
            ("validate_daily", "validation_scenarios.json", "gateway_contract"),
        ],
            "AGENTS.md": [
            ("read order", "reading order", "start here", "before changing code, read", "first read", "first 10 minutes", "先读", "先看"),
            ("do not", "must not", "不要"),
            ("quality-gate", "quality gate"),
        ],
    }

    for name, needles in quality_files.items():
        path = Path("/app/workspace/quality") / name if name != "AGENTS.md" else Path("/app/workspace/AGENTS.md")
        text = path.read_text(encoding="utf-8").lower()
        assert "todo" not in text
        for needle in needles:
            if isinstance(needle, tuple):
                assert any(option in text for option in needle), f"{needle!r} missing from {path}"
            else:
                assert needle in text, f"{needle!r} missing from {path}"

    test_functional_text = (Path("/app/workspace/quality") / "test_functional.py").read_text(encoding="utf-8").lower()
    assert any(keyword in test_functional_text for keyword in ("dirty_incident_batch", "dirty_ledger", "dirty incident"))
    assert any(keyword in test_functional_text for keyword in ("reference_batch", "reference_ledger"))
    assert any(keyword in test_functional_text for keyword in ("validate_daily", "validation_scenarios.json", "gateway_contract"))
