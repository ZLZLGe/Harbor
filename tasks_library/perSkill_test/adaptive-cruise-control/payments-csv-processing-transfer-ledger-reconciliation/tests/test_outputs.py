import json
from pathlib import Path

import pandas as pd
import pandas.testing as pdt


PAYMENTS_PATH = Path("/root/payments_ledger.csv")
REFUNDS_PATH = Path("/root/refund_ledger.csv")
SCRIPT_PATH = Path("/root/reconcile_ledgers.py")
OUTPUT_PATH = Path("/root/reconciliation_exceptions.csv")
SUMMARY_PATH = Path("/root/reconciliation_summary.json")


def test_required_files_exist():
    assert PAYMENTS_PATH.exists()
    assert REFUNDS_PATH.exists()
    assert SCRIPT_PATH.exists(), "reconcile_ledgers.py must exist"
    assert OUTPUT_PATH.exists(), "reconciliation_exceptions.csv must exist"
    assert SUMMARY_PATH.exists(), "reconciliation_summary.json must exist"


def test_input_files_shape():
    payments = pd.read_csv(PAYMENTS_PATH)
    refunds = pd.read_csv(REFUNDS_PATH)

    assert list(payments.columns) == [
        "payment_id",
        "order_id",
        "posted_at",
        "payment_status",
        "payment_method",
        "attempt_seq",
        "intended_order_amount",
        "charged_amount",
        "currency",
        "customer_region",
    ]
    assert len(payments) == 11
    assert set(payments["payment_status"]) == {"settled", "failed"}
    assert payments["order_id"].nunique() == 8

    assert list(refunds.columns) == [
        "refund_id",
        "order_id",
        "requested_at",
        "refund_status",
        "refund_reason",
        "refund_amount",
        "linked_payment_id",
    ]
    assert len(refunds) == 6
    assert set(refunds["refund_status"]) == {"completed", "pending", "cancelled"}


def test_output_rows_and_sort_order():
    output = pd.read_csv(OUTPUT_PATH, keep_default_na=False)

    expected = pd.DataFrame(
        [
            {
                "order_id": "ORD-1003",
                "customer_region": "EU",
                "expected_net_amount": 60.0,
                "settled_payment_total": 60.0,
                "completed_refund_total": 80.0,
                "open_refund_total": 0.0,
                "actual_net_amount": -20.0,
                "duplicate_charge_amount": 0.0,
                "over_refund_amount": 20.0,
                "net_gap_amount": 80.0,
                "exception_types": "over_refund",
                "review_priority": "critical",
                "latest_payment_at": "2026-08-01T09:30",
                "latest_refund_at": "2026-08-02T12:00",
                "settled_payment_ids": "PAY-1003-A",
                "open_refund_ids": "",
            },
            {
                "order_id": "ORD-1008",
                "customer_region": "APAC",
                "expected_net_amount": 50.0,
                "settled_payment_total": 100.0,
                "completed_refund_total": 120.0,
                "open_refund_total": 0.0,
                "actual_net_amount": -20.0,
                "duplicate_charge_amount": 50.0,
                "over_refund_amount": 20.0,
                "net_gap_amount": 70.0,
                "exception_types": "duplicate_charge|over_refund",
                "review_priority": "critical",
                "latest_payment_at": "2026-08-01T11:02",
                "latest_refund_at": "2026-08-02T12:50",
                "settled_payment_ids": "PAY-1008-A;PAY-1008-B",
                "open_refund_ids": "",
            },
            {
                "order_id": "ORD-1005",
                "customer_region": "LATAM",
                "expected_net_amount": 90.0,
                "settled_payment_total": 180.0,
                "completed_refund_total": 0.0,
                "open_refund_total": 20.0,
                "actual_net_amount": 180.0,
                "duplicate_charge_amount": 90.0,
                "over_refund_amount": 0.0,
                "net_gap_amount": 90.0,
                "exception_types": "duplicate_charge|open_refund",
                "review_priority": "high",
                "latest_payment_at": "2026-08-01T10:03",
                "latest_refund_at": "2026-08-02T12:20",
                "settled_payment_ids": "PAY-1005-A;PAY-1005-B",
                "open_refund_ids": "REF-1005-A",
            },
            {
                "order_id": "ORD-1002",
                "customer_region": "US",
                "expected_net_amount": 75.0,
                "settled_payment_total": 150.0,
                "completed_refund_total": 0.0,
                "open_refund_total": 0.0,
                "actual_net_amount": 150.0,
                "duplicate_charge_amount": 75.0,
                "over_refund_amount": 0.0,
                "net_gap_amount": 75.0,
                "exception_types": "duplicate_charge",
                "review_priority": "medium",
                "latest_payment_at": "2026-08-01T09:17",
                "latest_refund_at": "",
                "settled_payment_ids": "PAY-1002-A;PAY-1002-B",
                "open_refund_ids": "",
            },
            {
                "order_id": "ORD-1004",
                "customer_region": "APAC",
                "expected_net_amount": 200.0,
                "settled_payment_total": 200.0,
                "completed_refund_total": 0.0,
                "open_refund_total": 50.0,
                "actual_net_amount": 200.0,
                "duplicate_charge_amount": 0.0,
                "over_refund_amount": 0.0,
                "net_gap_amount": 0.0,
                "exception_types": "open_refund",
                "review_priority": "medium",
                "latest_payment_at": "2026-08-01T09:45",
                "latest_refund_at": "2026-08-02T12:10",
                "settled_payment_ids": "PAY-1004-A",
                "open_refund_ids": "REF-1004-A",
            },
        ]
    )

    assert list(output.columns) == list(expected.columns)
    pdt.assert_frame_equal(output, expected, check_dtype=False)


def test_normal_orders_are_excluded():
    output = pd.read_csv(OUTPUT_PATH, keep_default_na=False)
    assert "ORD-1001" not in set(output["order_id"])
    assert "ORD-1006" not in set(output["order_id"])
    assert "ORD-1007" not in set(output["order_id"])


def test_summary_metrics():
    with SUMMARY_PATH.open() as handle:
        summary = json.load(handle)

    assert summary == {
        "orders_processed": 8,
        "exception_order_count": 5,
        "priority_counts": {
            "critical": 2,
            "high": 1,
            "medium": 2,
        },
        "duplicate_charge_orders": 3,
        "over_refund_orders": 2,
        "open_refund_orders": 2,
        "total_duplicate_charge_amount": 215.0,
        "total_over_refund_amount": 40.0,
        "total_open_refund_amount": 70.0,
        "highest_net_gap_amount": 90.0,
        "orders_with_negative_actual_net": ["ORD-1003", "ORD-1008"],
    }
