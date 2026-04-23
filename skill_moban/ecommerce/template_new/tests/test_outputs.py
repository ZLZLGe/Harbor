from __future__ import annotations

import csv
import json
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path


OUTPUT_DIR = Path("/root/output")
CSV_PATH = OUTPUT_DIR / "fulfillment_exceptions.csv"
SUMMARY_PATH = OUTPUT_DIR / "order_reconciliation_summary.json"
MANIFEST_PATH = Path("/root/data/merchant_manifest.json")
CATALOG_PATH = Path("/root/data/catalog_export.csv")

FIELDNAMES = [
    "order_id",
    "order_name",
    "line_item_id",
    "sku",
    "variant_id",
    "issue_code",
    "severity",
    "expected_action",
    "evidence",
]

ISSUES = [
    "SKU_VARIANT_DRIFT",
    "FULFILLMENT_SERVICE_MISMATCH",
    "INSUFFICIENT_AVAILABLE_STOCK",
    "STALE_OR_CONFLICTING_TRACKING",
    "MISSING_TRACKING_FOR_SHIPPED_ITEM",
]

ALLOWED_SEVERITY = {"critical", "high", "medium"}
ALLOWED_ACTIONS = {"hold_order", "correct_sku_mapping", "reroute_fulfillment", "refresh_tracking", "manual_review"}

ORDERS_QUERY = "query Orders($first: Int!, $after: String, $start: String, $end: String) { orders(first: $first, after: $after, start: $start, end: $end) { edges { cursor node { id name processedAt financialStatus cancelledAt lineItems } } pageInfo { hasNextPage endCursor } } }"
VARIANTS_QUERY = "query Variants($first: Int!, $after: String, $sku: String, $activeOnly: Boolean) { productVariants(first: $first, after: $after, sku: $sku, activeOnly: $activeOnly) { edges { cursor node { id sku active inventoryItemId fulfillmentService } } pageInfo { hasNextPage endCursor } } }"


def post_json(url: str, payload: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Client": "verifier-main"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_json(url: str) -> dict | None:
    req = urllib.request.Request(url, headers={"X-Client": "verifier-main"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def paginate_graphql(url: str, query: str, root: str, variables: dict) -> list[dict]:
    out = []
    after = None
    while True:
        merged = dict(variables)
        merged["after"] = after
        payload = post_json(url, {"query": query, "variables": merged})
        connection = payload["data"][root]
        out.extend(edge["node"] for edge in connection["edges"])
        if not connection["pageInfo"]["hasNextPage"]:
            return out
        after = connection["pageInfo"]["endCursor"]


def read_catalog() -> dict[str, dict]:
    with CATALOG_PATH.open(newline="", encoding="utf-8") as fh:
        return {row["sku"]: row for row in csv.DictReader(fh)}


def expected_rows_and_summary() -> tuple[list[dict], dict]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    catalog = read_catalog()
    window = manifest["reconciliation_window"]
    graphql_url = manifest["service_urls"]["commerce_admin_graphql"]
    warehouse_url = manifest["service_urls"]["warehouse"]
    carrier_url = manifest["service_urls"]["carrier_tracking"]

    orders = paginate_graphql(
        graphql_url,
        ORDERS_QUERY,
        "orders",
        {"first": 3, "start": window["start"], "end": window["end"]},
    )
    variant_cache: dict[str, list[dict]] = {}
    expected: list[dict] = []
    orders_checked = 0
    line_items_checked = 0

    def add(order: dict, item: dict, code: str, severity: str, action: str) -> None:
        expected.append({
            "order_id": order["id"],
            "order_name": order["name"],
            "line_item_id": item["id"],
            "sku": item["sku"],
            "variant_id": item["variantId"],
            "issue_code": code,
            "severity": severity,
            "expected_action": action,
        })

    for order in orders:
        shippable = [li for li in order["lineItems"] if li.get("requiresShipping")]
        if order["financialStatus"] != "PAID" or order.get("cancelledAt") or not shippable:
            continue
        orders_checked += 1
        for item in shippable:
            line_items_checked += 1
            sku = item["sku"]
            variant_cache.setdefault(
                sku,
                paginate_graphql(graphql_url, VARIANTS_QUERY, "productVariants", {"first": 20, "sku": sku, "activeOnly": True}),
            )
            variants = variant_cache[sku]
            resolved = variants[0] if len(variants) == 1 else None
            if len(variants) != 1 or (resolved and resolved["id"] != item["variantId"]):
                add(order, item, "SKU_VARIANT_DRIFT", "critical", "correct_sku_mapping")
                continue

            expected_service = catalog.get(sku, {}).get("expected_fulfillment_service")
            if expected_service and resolved["fulfillmentService"] != expected_service:
                add(order, item, "FULFILLMENT_SERVICE_MISMATCH", "high", "reroute_fulfillment")

            unfulfilled = int(item.get("unfulfilledQuantity") or 0)
            inv = resolved["inventoryItemId"]
            if unfulfilled > 0:
                encoded = urllib.parse.urlencode({"inventory_item_id": inv})
                stock = get_json(f"{warehouse_url}/stock?{encoded}") or {}
                reservations = get_json(f"{warehouse_url}/reservations?{encoded}") or {"reservations": []}
                reserved_qty = sum(int(r["quantity"]) for r in reservations.get("reservations", []) if r.get("status") == "open")
                available = int(stock.get("on_hand", 0)) - reserved_qty
                if available < unfulfilled:
                    add(order, item, "INSUFFICIENT_AVAILABLE_STOCK", "critical", "hold_order")

            status = item.get("fulfillmentStatus")
            tracking = item.get("trackingNumber")
            if status in {"FULFILLED", "SHIPPED", "IN_TRANSIT"}:
                carrier = get_json(f"{carrier_url}/track/{urllib.parse.quote(str(tracking or ''))}") if tracking else None
                if not carrier:
                    add(order, item, "MISSING_TRACKING_FOR_SHIPPED_ITEM", "medium", "refresh_tracking")
                elif status in {"UNFULFILLED", "PARTIAL", "IN_TRANSIT"} and carrier.get("latest_status") in {"delivered", "cancelled", "exception"}:
                    add(order, item, "STALE_OR_CONFLICTING_TRACKING", "high", "manual_review")

    counts = Counter(row["issue_code"] for row in expected)
    summary = {
        "window": {"start": window["start"], "end": window["end"]},
        "totals": {
            "orders_checked": orders_checked,
            "line_items_checked": line_items_checked,
            "orders_with_exceptions": len({row["order_id"] for row in expected}),
            "exception_rows": len(expected),
        },
        "issue_counts": {issue: counts.get(issue, 0) for issue in ISSUES},
        "source_checks": {
            "commerce_admin": True,
            "warehouse_reservations": True,
            "carrier_tracking": True,
        },
    }
    return sorted(expected, key=lambda r: (r["order_id"], r["line_item_id"], r["issue_code"])), summary


def read_submission() -> tuple[list[dict], dict]:
    assert CSV_PATH.exists(), "Missing /root/output/fulfillment_exceptions.csv"
    assert SUMMARY_PATH.exists(), "Missing /root/output/order_reconciliation_summary.json"
    with CSV_PATH.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        assert reader.fieldnames == FIELDNAMES, f"CSV columns must be exactly {FIELDNAMES}"
        rows = list(reader)
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    return rows, summary


def test_output_files_exist_and_parse() -> None:
    rows, summary = read_submission()
    assert isinstance(rows, list)
    assert isinstance(summary, dict)
    assert "totals" in summary
    assert "issue_counts" in summary


def test_exception_rows_match_live_recomputation() -> None:
    rows, _ = read_submission()
    expected, _ = expected_rows_and_summary()
    comparison_fields = [
        "order_id",
        "order_name",
        "line_item_id",
        "sku",
        "variant_id",
        "issue_code",
        "severity",
    ]
    comparable = sorted(
        [{key: row[key] for key in comparison_fields} for row in rows],
        key=lambda r: (r["order_id"], r["line_item_id"], r["issue_code"]),
    )
    expected_comparable = sorted(
        [{key: row[key] for key in comparison_fields} for row in expected],
        key=lambda r: (r["order_id"], r["line_item_id"], r["issue_code"]),
    )
    assert comparable == expected_comparable


def test_summary_matches_csv_and_live_recomputation() -> None:
    rows, summary = read_submission()
    _, expected_summary = expected_rows_and_summary()
    assert summary["window"] == expected_summary["window"]
    assert summary["totals"] == expected_summary["totals"]
    assert summary["issue_counts"] == expected_summary["issue_counts"]
    assert summary["source_checks"] == expected_summary["source_checks"]
    assert summary["totals"]["exception_rows"] == len(rows)
    assert summary["totals"]["orders_with_exceptions"] == len({row["order_id"] for row in rows})


def test_schema_values_and_evidence_quality() -> None:
    rows, summary = read_submission()
    assert set(summary["issue_counts"]) == set(ISSUES)
    assert rows, "Expected at least one exception row"
    for row in rows:
        assert row["issue_code"] in ISSUES
        assert row["severity"] in ALLOWED_SEVERITY
        assert row["expected_action"] in ALLOWED_ACTIONS
        evidence = json.loads(row["evidence"])
        assert evidence["admin_order_id"] == row["order_id"]
        assert evidence["line_item_id"] == row["line_item_id"]
        assert evidence["sku"] == row["sku"]
        assert isinstance(evidence.get("checked_sources"), list)
        if row["issue_code"] == "SKU_VARIANT_DRIFT":
            assert "active_variant_ids" in evidence
            assert "commerce_admin" in evidence["checked_sources"]
        elif row["issue_code"] == "FULFILLMENT_SERVICE_MISMATCH":
            fulfillment_keys = {key for key in evidence if "fulfillment" in key.lower() or "service" in key.lower()}
            assert len(fulfillment_keys) >= 2
        elif row["issue_code"] == "INSUFFICIENT_AVAILABLE_STOCK":
            assert "available_quantity" in evidence
            assert "reservation_ids" in evidence
        elif row["issue_code"] == "STALE_OR_CONFLICTING_TRACKING":
            assert evidence["carrier_status"] in {"delivered", "cancelled", "exception"}
            assert "tracking_number" in evidence
        elif row["issue_code"] == "MISSING_TRACKING_FOR_SHIPPED_ITEM":
            assert "tracking_number" in evidence
            assert evidence["admin_fulfillment_status"] in {"FULFILLED", "SHIPPED", "IN_TRANSIT"}
