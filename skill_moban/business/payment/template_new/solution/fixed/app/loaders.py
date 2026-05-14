from __future__ import annotations

import csv
import json
from pathlib import Path

import yaml


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_ndjson(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def load_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_all(data_root: Path) -> dict:
    manifest = load_json(data_root / "billing_manifest.json")
    catalog = load_json(data_root / "plan_catalog_seed.json")
    subscriptions = load_ndjson(data_root / "subscription_snapshot.ndjson")
    invoices = load_ndjson(data_root / "invoice_snapshot.ndjson")
    changes = load_csv(data_root / "change_requests.csv")
    usage = load_csv(data_root / "usage_rollups.csv")
    policy = load_yaml(data_root / "billing_policy.yaml")

    prices_by_id = {price["id"]: price for price in catalog["prices"]}
    products_by_id = {product["product_id"]: product for product in catalog["products"]}
    plan_to_price_id = {
        products_by_id[price["product"]]["plan_id"]: price["id"]
        for price in catalog["prices"]
        if price["usage_type"] == "licensed"
    }

    subscriptions_by_id = {item["subscription_id"]: item for item in subscriptions}
    invoices_by_subscription = {item["subscription_id"]: item for item in invoices}

    changes_by_subscription: dict[str, list[dict]] = {}
    for item in changes:
        changes_by_subscription.setdefault(item["subscription_id"], []).append(item)
    for items in changes_by_subscription.values():
        items.sort(key=lambda row: (row["effective_date"], row["change_request_id"]))

    usage_by_subscription: dict[str, list[dict]] = {}
    for item in usage:
        usage_by_subscription.setdefault(item["subscription_id"], []).append(item)

    return {
        "manifest": manifest,
        "catalog": catalog,
        "policy": policy,
        "prices_by_id": prices_by_id,
        "plan_to_price_id": plan_to_price_id,
        "subscriptions_by_id": subscriptions_by_id,
        "invoices_by_subscription": invoices_by_subscription,
        "changes_by_subscription": changes_by_subscription,
        "usage_by_subscription": usage_by_subscription,
    }
