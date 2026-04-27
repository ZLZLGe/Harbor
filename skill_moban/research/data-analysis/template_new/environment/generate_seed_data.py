#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"


STORES = [
    {"store_id": "SFO-01", "region": "West", "timezone": "America/Los_Angeles"},
    {"store_id": "NYC-02", "region": "East", "timezone": "America/New_York"},
    {"store_id": "CHI-03", "region": "Central", "timezone": "America/Chicago"},
    {"store_id": "PHX-04", "region": "Mountain", "timezone": "America/Phoenix"},
]

PRODUCTS = [
    {"product_id": "P-APPLE", "category_id": "produce", "category_name": "Produce", "unit_cost": 1.10, "active": "true"},
    {"product_id": "P-BERRY", "category_id": "produce", "category_name": "Produce", "unit_cost": 2.40, "active": "true"},
    {"product_id": "P-MILK", "category_id": "dairy", "category_name": "Dairy", "unit_cost": 1.80, "active": "true"},
    {"product_id": "P-YOGURT", "category_id": "dairy", "category_name": "Dairy", "unit_cost": 0.95, "active": "true"},
    {"product_id": "P-PASTA", "category_id": "pantry", "category_name": "Pantry", "unit_cost": 1.25, "active": "true"},
    {"product_id": "P-SAUCE", "category_id": "pantry", "category_name": "Pantry", "unit_cost": 1.45, "active": "true"},
]

PROMOS = [
    {
        "promo_id": "PROMO-SPRING-PRODUCE",
        "category_id": "produce",
        "business_start_date": "2026-03-15",
        "business_end_date": "2026-03-21",
        "promo_spend": 120.0,
    },
    {
        "promo_id": "PROMO-DAIRY-BOOST",
        "category_id": "dairy",
        "business_start_date": "2026-03-18",
        "business_end_date": "2026-03-24",
        "promo_spend": 96.0,
    },
    {
        "promo_id": "PROMO-PANTRY-VALUE",
        "category_id": "pantry",
        "business_start_date": "2026-03-22",
        "business_end_date": "2026-03-28",
        "promo_spend": 80.0,
    },
]

TRAFFIC_BASE = {
    "SFO-01": 1.08,
    "NYC-02": 1.18,
    "CHI-03": 0.96,
    "PHX-04": 0.90,
}

STORE_MULT = {
    "SFO-01": 1.18,
    "NYC-02": 1.32,
    "CHI-03": 0.94,
    "PHX-04": 0.86,
}

CATEGORY_BASE = {
    "produce": 46.0,
    "dairy": 38.0,
    "pantry": 31.0,
}

PROMO_EFFECT = {
    ("SFO-01", "produce"): 1.34,
    ("NYC-02", "produce"): 1.28,
    ("CHI-03", "produce"): 1.04,
    ("PHX-04", "produce"): 1.19,
    ("SFO-01", "dairy"): 1.11,
    ("NYC-02", "dairy"): 1.33,
    ("CHI-03", "dairy"): 1.22,
    ("PHX-04", "dairy"): 0.96,
    ("SFO-01", "pantry"): 0.98,
    ("NYC-02", "pantry"): 1.12,
    ("CHI-03", "pantry"): 1.30,
    ("PHX-04", "pantry"): 1.21,
}


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def local_noon_utc(store: dict[str, str], day: datetime) -> datetime:
    local = datetime(day.year, day.month, day.day, 12, 0, tzinfo=ZoneInfo(store["timezone"]))
    return local.astimezone(timezone.utc)


def order_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    start = datetime(2026, 3, 8)
    end = datetime(2026, 3, 31)
    product_by_category = {
        "produce": [p for p in PRODUCTS if p["category_id"] == "produce"],
        "dairy": [p for p in PRODUCTS if p["category_id"] == "dairy"],
        "pantry": [p for p in PRODUCTS if p["category_id"] == "pantry"],
    }
    event_counter = 1
    current = start
    while current <= end:
        weekday_factor = 1.16 if current.weekday() in (4, 5, 6) else 0.95
        for store in STORES:
            traffic = traffic_index(store["store_id"], current)
            for category, products in product_by_category.items():
                active_promo = promo_for_category(category, current)
                effect = 1.0
                discount_rate = 0.0
                if active_promo:
                    effect = PROMO_EFFECT[(store["store_id"], category)]
                    discount_rate = {"produce": 0.11, "dairy": 0.09, "pantry": 0.07}[category]
                if weather_anomaly(store["store_id"], current):
                    effect *= 0.72
                if holiday(current):
                    effect *= 0.82
                base_orders = CATEGORY_BASE[category] * STORE_MULT[store["store_id"]] * weekday_factor * traffic * effect
                n_orders = max(4, int(round(base_orders / 3.8)))
                for i in range(n_orders):
                    product = products[(i + current.day + len(store["store_id"])) % len(products)]
                    qty = 1 + ((i + current.day) % 3 == 0)
                    price = {"produce": 3.8, "dairy": 4.4, "pantry": 3.6}[category]
                    price += (0.35 if product["product_id"].endswith("BERRY") else 0.0)
                    discount = round(price * qty * discount_rate, 2)
                    order_id = f"O-{store['store_id']}-{current:%Y%m%d}-{category}-{i:03d}"
                    event_time = local_noon_utc(store, current) + timedelta(minutes=(i * 13) % 480)
                    ingested = event_time + timedelta(minutes=2)
                    status = "completed"
                    if (i + current.day + len(category)) % 41 == 0:
                        status = "cancelled"
                    rows.append(
                        {
                            "event_id": f"E{event_counter:06d}",
                            "order_id": order_id,
                            "store_id": store["store_id"],
                            "product_id": product["product_id"],
                            "event_at_utc": event_time.isoformat().replace("+00:00", "Z"),
                            "ingested_at_utc": ingested.isoformat().replace("+00:00", "Z"),
                            "quantity": qty,
                            "unit_price": f"{price:.2f}",
                            "unit_cost": f"{product['unit_cost']:.2f}",
                            "discount_amount": f"{discount:.2f}",
                            "status": status,
                        }
                    )
                    event_counter += 1
                    if (i + current.day) % 37 == 0:
                        duplicate = dict(rows[-1])
                        duplicate["event_id"] = f"E{event_counter:06d}"
                        duplicate["ingested_at_utc"] = (ingested + timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
                        rows.append(duplicate)
                        event_counter += 1
                    if status == "completed" and (i + current.day + len(store["store_id"])) % 53 == 0:
                        correction = dict(rows[-1])
                        correction["event_id"] = f"E{event_counter:06d}"
                        correction["event_at_utc"] = (event_time + timedelta(hours=3)).isoformat().replace("+00:00", "Z")
                        correction["ingested_at_utc"] = (ingested + timedelta(hours=5)).isoformat().replace("+00:00", "Z")
                        correction["status"] = "returned"
                        rows.append(correction)
                        event_counter += 1
        current += timedelta(days=1)
    return rows


def promo_for_category(category: str, day: datetime) -> dict[str, object] | None:
    for promo in PROMOS:
        if promo["category_id"] != category:
            continue
        start = datetime.fromisoformat(str(promo["business_start_date"]))
        end = datetime.fromisoformat(str(promo["business_end_date"]))
        if start <= day <= end:
            return promo
    return None


def traffic_index(store_id: str, day: datetime) -> float:
    wave = 0.06 * math.sin((day.day - 6) / 3.0)
    return round(TRAFFIC_BASE[store_id] + wave, 3)


def weather_anomaly(store_id: str, day: datetime) -> bool:
    return (store_id, day.strftime("%Y-%m-%d")) in {
        ("NYC-02", "2026-03-16"),
        ("NYC-02", "2026-03-17"),
        ("PHX-04", "2026-03-23"),
        ("CHI-03", "2026-03-27"),
    }


def holiday(day: datetime) -> bool:
    return day.strftime("%Y-%m-%d") in {"2026-03-17"}


def external_rows() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    weather_rows = []
    traffic_rows = []
    current = datetime(2026, 3, 8)
    while current <= datetime(2026, 3, 31):
        for store in STORES:
            anomaly = weather_anomaly(store["store_id"], current)
            weather_rows.append(
                {
                    "store_id": store["store_id"],
                    "business_date": current.strftime("%Y-%m-%d"),
                    "weather_anomaly": "true" if anomaly else "false",
                    "temperature_f": 48 + current.day % 19 + (9 if store["store_id"] == "PHX-04" else 0),
                    "precipitation_in": "1.20" if anomaly else "0.02",
                }
            )
            traffic_rows.append(
                {
                    "store_id": store["store_id"],
                    "business_date": current.strftime("%Y-%m-%d"),
                    "traffic_index": f"{traffic_index(store['store_id'], current):.3f}",
                    "holiday": "true" if holiday(current) else "false",
                }
            )
        current += timedelta(days=1)
    return weather_rows, traffic_rows


def inventory_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    event_counter = 1
    stockout_cases = {
        ("CHI-03", "P-PASTA", "2026-03-24"): (10, 19),
        ("CHI-03", "P-SAUCE", "2026-03-25"): (12, 20),
        ("PHX-04", "P-MILK", "2026-03-20"): (9, 18),
        ("SFO-01", "P-BERRY", "2026-03-18"): (14, 18),
        ("NYC-02", "P-APPLE", "2026-03-17"): (8, 14),
    }
    for store in STORES:
        tz = ZoneInfo(store["timezone"])
        for product in PRODUCTS:
            current = datetime(2026, 3, 8)
            while current <= datetime(2026, 3, 31):
                local_start = datetime(current.year, current.month, current.day, 0, 0, tzinfo=tz)
                first = local_start + timedelta(minutes=5)
                rows.append(
                    {
                        "inventory_event_id": f"I{event_counter:05d}",
                        "store_id": store["store_id"],
                        "product_id": product["product_id"],
                        "event_at_utc": first.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                        "ingested_at_utc": (first + timedelta(minutes=1)).astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                        "on_hand": 28,
                    }
                )
                event_counter += 1
                key = (store["store_id"], product["product_id"], current.strftime("%Y-%m-%d"))
                if key in stockout_cases:
                    start_hour, end_hour = stockout_cases[key]
                    down = local_start + timedelta(hours=start_hour)
                    up = local_start + timedelta(hours=end_hour)
                    rows.append(
                        {
                            "inventory_event_id": f"I{event_counter:05d}",
                            "store_id": store["store_id"],
                            "product_id": product["product_id"],
                            "event_at_utc": down.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                            "ingested_at_utc": (down + timedelta(minutes=4)).astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                            "on_hand": 0,
                        }
                    )
                    event_counter += 1
                    rows.append(
                        {
                            "inventory_event_id": f"I{event_counter:05d}",
                            "store_id": store["store_id"],
                            "product_id": product["product_id"],
                            "event_at_utc": up.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                            "ingested_at_utc": (up + timedelta(minutes=7)).astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                            "on_hand": 22,
                        }
                    )
                    event_counter += 1
                current += timedelta(days=1)
    return rows


def main() -> None:
    write_csv(DATA / "catalog" / "stores.csv", STORES, ["store_id", "region", "timezone"])
    write_csv(DATA / "catalog" / "products.csv", PRODUCTS, ["product_id", "category_id", "category_name", "unit_cost", "active"])
    write_csv(
        DATA / "catalog" / "promotions.csv",
        PROMOS,
        ["promo_id", "category_id", "business_start_date", "business_end_date", "promo_spend"],
    )
    write_csv(
        DATA / "pos" / "transaction_events.csv",
        order_rows(),
        [
            "event_id",
            "order_id",
            "store_id",
            "product_id",
            "event_at_utc",
            "ingested_at_utc",
            "quantity",
            "unit_price",
            "unit_cost",
            "discount_amount",
            "status",
        ],
    )
    write_csv(
        DATA / "inventory" / "inventory_snapshots.csv",
        inventory_rows(),
        ["inventory_event_id", "store_id", "product_id", "event_at_utc", "ingested_at_utc", "on_hand"],
    )
    weather_rows, traffic_rows = external_rows()
    write_csv(
        DATA / "external" / "weather_daily.csv",
        weather_rows,
        ["store_id", "business_date", "weather_anomaly", "temperature_f", "precipitation_in"],
    )
    write_csv(
        DATA / "external" / "traffic_daily.csv",
        traffic_rows,
        ["store_id", "business_date", "traffic_index", "holiday"],
    )
    (DATA / "catalog" / "analysis_contract.json").write_text(
        json.dumps(
            {
                "baseline_days": 7,
                "alpha": 0.10,
                "stockout_penalty_per_hour": 0.035,
                "reportable_min_adjusted_roi": 0.15,
                "reportable_max_stockout_hours": 10.0,
                "risk_thresholds": {"high_stockout_hours": 7.0, "high_return_rate": 0.06, "high_duplicate_rate": 0.03},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
