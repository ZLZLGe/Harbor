from __future__ import annotations

import csv
import gzip
import json
import os
import re
import shutil
import subprocess
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo


WORKSPACE = Path("/app/workspace")
DATA_DIR = WORKSPACE / "data"
RUNNER = WORKSPACE / "run.sh"
SQL_FILE = WORKSPACE / "sql" / "build_waves.sql"
ANSWER = Path("/app/answer")

WAVE_FIELDS = [
    "warehouse_id",
    "route_id",
    "business_date",
    "wave_id",
    "wave_start_utc",
    "wave_end_utc",
    "loaded_packages",
    "valid_orders",
    "delivered_packages",
    "late_packages",
    "missing_delivery_packages",
    "stockout_impacted_packages",
    "stockout_exposure_minutes",
    "late_rate",
    "wave_status",
]

LONGEST_FIELDS = [
    "warehouse_id",
    "route_id",
    "business_date",
    "wave_id",
    "loaded_packages",
    "wave_duration_minutes",
    "late_rate",
    "stockout_exposure_minutes",
]

AUDIT_FIELDS = [
    "order_id",
    "package_id",
    "warehouse_id",
    "route_id",
    "business_date",
    "wave_id",
    "order_final_status",
    "loaded_at_utc",
    "delivered_at_utc",
    "sla_deadline_utc",
    "sla_status",
    "stockout_impacted",
]


def parse_ts(value: str) -> datetime:
    if not value:
        raise ValueError("empty timestamp")
    return datetime.fromisoformat(value.replace(" ", "T")).replace(tzinfo=timezone.utc)


def fmt_ts(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def canonical_wave_id(value: object) -> str:
    text = str(value)
    return text.rsplit("-", 1)[-1]


def read_csv(path: Path) -> list[dict[str, str]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_jsonl_gz(path: Path) -> list[dict[str, object]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]], gz: bool = False) -> None:
    opener = gzip.open if gz else open
    with opener(path, "wt", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl_gz(path: Path, rows: list[dict[str, object]]) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")


def local_business_date(ts: datetime, tz_name: str) -> str:
    return ts.astimezone(ZoneInfo(tz_name)).date().isoformat()


@dataclass
class LoadRow:
    scan_id: str
    package_id: str
    order_id: str
    warehouse_id: str
    route_id: str
    sku_id: str
    loaded_at: datetime
    business_date: str
    order_final_status: str
    delivered_at: datetime | None
    sla_minutes: int
    wave_id: str = ""
    wave_start: datetime | None = None
    wave_end: datetime | None = None
    sla_status: str = ""
    stockout_impacted: int = 0
    is_valid_order: bool = True


def compute_expected(data_dir: Path):
    warehouses = {r["warehouse_id"]: r["timezone"] for r in read_csv(data_dir / "reference" / "warehouses.csv")}
    active_skus = {r["sku_id"] for r in read_csv(data_dir / "reference" / "skus.csv") if str(r["active"]) in {"1", "true", "True"}}
    sla = {(r["warehouse_id"], r["route_id"]): int(r["sla_minutes"]) for r in read_csv(data_dir / "reference" / "route_sla.csv")}
    scan_rows = read_csv(data_dir / "package_scans" / "scans.csv.gz")
    order_rows = read_jsonl_gz(data_dir / "order_events" / "events.jsonl.gz")
    inv_rows = read_csv(data_dir / "inventory_snapshots" / "snapshots.csv.gz")

    scans_by_id = {}
    for row in scan_rows:
        old = scans_by_id.get(row["scan_id"])
        key = (parse_ts(row["ingested_at"]), parse_ts(row["event_time"]))
        if old is None or key > (parse_ts(old["ingested_at"]), parse_ts(old["event_time"])):
            scans_by_id[row["scan_id"]] = row
    scans = list(scans_by_id.values())

    final_orders = {}
    for row in order_rows:
        key = (parse_ts(str(row["event_time"])), int(row["event_version"]), parse_ts(str(row["ingested_at"])))
        old = final_orders.get(str(row["order_id"]))
        if old is None or key > old[0]:
            final_orders[str(row["order_id"])] = (key, str(row["status"]))

    delivered = {}
    for row in scans:
        if row["scan_type"] == "DELIVERED":
            ts = parse_ts(row["event_time"])
            old = delivered.get(row["package_id"])
            if old is None or ts < old:
                delivered[row["package_id"]] = ts

    snapshots_by_id = {}
    for row in inv_rows:
        old = snapshots_by_id.get(row["snapshot_id"])
        key = (parse_ts(row["ingested_at"]), parse_ts(row["event_time"]))
        if old is None or key > (parse_ts(old["ingested_at"]), parse_ts(old["event_time"])):
            snapshots_by_id[row["snapshot_id"]] = row

    grouped_inv = defaultdict(list)
    for row in snapshots_by_id.values():
        if row["sku_id"] in active_skus:
            grouped_inv[(row["warehouse_id"], row["sku_id"])].append(row)

    stockout_intervals = []
    for (warehouse_id, sku_id), rows in grouped_inv.items():
        rows.sort(key=lambda r: (parse_ts(r["event_time"]), parse_ts(r["ingested_at"]), r["snapshot_id"]))
        for current, nxt in zip(rows, rows[1:]):
            if int(current["available_to_promise"]) <= 0:
                start = parse_ts(current["event_time"])
                end = parse_ts(nxt["event_time"])
                if end > start:
                    stockout_intervals.append((warehouse_id, sku_id, start, end))

    loads = []
    invalid = {"CANCELLED", "PAYMENT_FAILED", "FRAUD_REJECTED"}
    for row in scans:
        if row["scan_type"] != "LOADED_ON_TRUCK":
            continue
        final_status = final_orders.get(row["order_id"], ((None,), ""))[1]
        loaded_at = parse_ts(row["event_time"])
        wh = row["warehouse_id"]
        loads.append(
            LoadRow(
                scan_id=row["scan_id"],
                package_id=row["package_id"],
                order_id=row["order_id"],
                warehouse_id=wh,
                route_id=row["route_id"],
                sku_id=row["sku_id"],
                loaded_at=loaded_at,
                business_date=local_business_date(loaded_at, warehouses[wh]),
                order_final_status=final_status,
                delivered_at=delivered.get(row["package_id"]),
                sla_minutes=sla[(wh, row["route_id"])],
                is_valid_order=bool(final_status) and final_status not in invalid,
            )
        )

    by_route_day = defaultdict(list)
    for load in loads:
        by_route_day[(load.warehouse_id, load.route_id, load.business_date)].append(load)

    for (wh, route, day), rows in by_route_day.items():
        rows.sort(key=lambda r: (r.loaded_at, r.package_id, r.scan_id))
        wave_seq = 0
        prev = None
        wave_members = []
        for row in rows:
            if prev is None or (row.loaded_at - prev).total_seconds() > 1200:
                if wave_members:
                    start = min(r.loaded_at for r in wave_members)
                    end = max(r.loaded_at for r in wave_members)
                    for member in wave_members:
                        member.wave_start = start
                        member.wave_end = end
                wave_seq += 1
                wave_members = []
            row.wave_id = f"{wh}-{route}-{day}-{wave_seq}"
            wave_members.append(row)
            prev = row.loaded_at
        if wave_members:
            start = min(r.loaded_at for r in wave_members)
            end = max(r.loaded_at for r in wave_members)
            for member in wave_members:
                member.wave_start = start
                member.wave_end = end

    for row in loads:
        assert row.wave_start is not None and row.wave_end is not None
        deadline = row.loaded_at.timestamp() + row.sla_minutes * 60
        if row.delivered_at is None:
            row.sla_status = "MISSING_DELIVERY"
        elif row.delivered_at.timestamp() > deadline:
            row.sla_status = "LATE"
        else:
            row.sla_status = "ON_TIME"
        for wh, sku, start, end in stockout_intervals:
            if wh == row.warehouse_id and sku == row.sku_id and start < row.wave_end and end > row.wave_start:
                row.stockout_impacted = 1

    valid_loads = [row for row in loads if row.is_valid_order]

    wave_groups = defaultdict(list)
    for row in loads:
        wave_groups[(row.warehouse_id, row.route_id, row.business_date, canonical_wave_id(row.wave_id))].append(row)

    wave_rows = {}
    for key, rows in wave_groups.items():
        wh, route, day, wave_id = key
        start = min(r.loaded_at for r in rows)
        end = max(r.loaded_at for r in rows)
        valid_rows = [r for r in rows if r.is_valid_order]
        wave_skus = {r.sku_id for r in valid_rows}
        exposure = 0
        for i_wh, sku, i_start, i_end in stockout_intervals:
            if i_wh == wh and sku in wave_skus and i_start < end and i_end > start:
                overlap_start = max(i_start, start)
                overlap_end = min(i_end, end)
                exposure += int((overlap_end - overlap_start).total_seconds() // 60)
        loaded = len(valid_rows)
        late = sum(1 for r in valid_rows if r.sla_status == "LATE")
        missing = sum(1 for r in valid_rows if r.sla_status == "MISSING_DELIVERY")
        wave_rows[key] = {
            "warehouse_id": wh,
            "route_id": route,
            "business_date": day,
            "wave_id": wave_id,
            "wave_start_utc": fmt_ts(start),
            "wave_end_utc": fmt_ts(end),
            "loaded_packages": loaded,
            "valid_orders": len({r.order_id for r in valid_rows}),
            "delivered_packages": sum(1 for r in valid_rows if r.sla_status != "MISSING_DELIVERY"),
            "late_packages": late,
            "missing_delivery_packages": missing,
            "stockout_impacted_packages": sum(r.stockout_impacted for r in valid_rows),
            "stockout_exposure_minutes": exposure,
            "late_rate": f"{(Decimal(late) / Decimal(loaded)) if loaded else Decimal(0):.4f}",
            "wave_status": "no_valid_orders" if loaded == 0 else ("incomplete" if missing else ("late" if late else "complete")),
        }

    audit_rows = {}
    for r in valid_loads:
        wave_id = canonical_wave_id(r.wave_id)
        audit_rows[(r.warehouse_id, r.route_id, r.business_date, wave_id, fmt_ts(r.loaded_at), r.package_id)] = {
            "order_id": r.order_id,
            "package_id": r.package_id,
            "warehouse_id": r.warehouse_id,
            "route_id": r.route_id,
            "business_date": r.business_date,
            "wave_id": wave_id,
            "order_final_status": r.order_final_status,
            "loaded_at_utc": fmt_ts(r.loaded_at),
            "delivered_at_utc": fmt_ts(r.delivered_at),
            "sla_deadline_utc": fmt_ts(datetime.fromtimestamp(r.loaded_at.timestamp() + r.sla_minutes * 60, tz=timezone.utc)),
            "sla_status": r.sla_status,
            "stockout_impacted": r.stockout_impacted,
        }

    longest = {}
    for key, row in wave_rows.items():
        group = key[:3]
        old = longest.get(group)
        if old is None or row["loaded_packages"] > old["loaded_packages"] or (
            row["loaded_packages"] == old["loaded_packages"] and row["wave_start_utc"] < old["_start"]
        ):
            copied = dict(row)
            copied["_start"] = row["wave_start_utc"]
            longest[group] = copied
    longest_rows = {}
    for group, row in longest.items():
        start = parse_ts(row["wave_start_utc"])
        end = parse_ts(row["wave_end_utc"])
        longest_rows[group] = {
            "warehouse_id": row["warehouse_id"],
            "route_id": row["route_id"],
            "business_date": row["business_date"],
            "wave_id": row["wave_id"],
            "loaded_packages": row["loaded_packages"],
            "wave_duration_minutes": int((end - start).total_seconds() // 60),
            "late_rate": row["late_rate"],
            "stockout_exposure_minutes": row["stockout_exposure_minutes"],
        }

    summary = {
        "n_package_scan_rows_loaded": len(scan_rows),
        "n_package_scan_rows_after_dedup": len(scans),
        "n_order_event_rows_loaded": len(order_rows),
        "n_valid_orders": sum(1 for _key, status in final_orders.values() if status not in invalid),
        "n_waves": len(wave_rows),
        "n_routes_with_waves": len({k[:2] for k in wave_rows}),
        "n_stockout_intervals": len(stockout_intervals),
    }
    return wave_rows, audit_rows, longest_rows, summary


def run(cmd: list[str], *, env: dict[str, str] | None = None, timeout: int = 180) -> str:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    completed = subprocess.run(cmd, text=True, capture_output=True, env=merged, timeout=timeout)
    if completed.returncode != 0:
        raise AssertionError(
            f"Command failed: {' '.join(cmd)}\nSTDOUT:\n{completed.stdout[-4000:]}\nSTDERR:\n{completed.stderr[-4000:]}"
        )
    return completed.stdout


def run_pipeline(data_dir: Path | None = None) -> None:
    env = {"DATA_DIR": str(data_dir)} if data_dir else None
    run(["bash", str(RUNNER), "--output", str(ANSWER)], env=env, timeout=240)


def read_answer_csv(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_answer_tsv(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def normalize_wave(rows: list[dict[str, str]]) -> dict[tuple[str, str, str, str], dict[str, object]]:
    normalized = {}
    for row in rows:
        wave_id = canonical_wave_id(row["wave_id"])
        key = (row["warehouse_id"], row["route_id"], row["business_date"], wave_id)
        normalized[key] = {
            **{k: row[k] for k in ["warehouse_id", "route_id", "business_date", "wave_start_utc", "wave_end_utc", "wave_status"]},
            "wave_id": wave_id,
            **{k: int(row[k]) for k in ["loaded_packages", "valid_orders", "delivered_packages", "late_packages", "missing_delivery_packages", "stockout_impacted_packages", "stockout_exposure_minutes"]},
            "late_rate": f"{Decimal(row['late_rate']):.4f}",
        }
    return normalized


def normalize_audit(rows: list[dict[str, str]]) -> dict[tuple[str, str, str, str, str, str], dict[str, object]]:
    normalized = {}
    for row in rows:
        wave_id = canonical_wave_id(row["wave_id"])
        key = (row["warehouse_id"], row["route_id"], row["business_date"], wave_id, row["loaded_at_utc"], row["package_id"])
        normalized[key] = {
            **{k: row[k] for k in AUDIT_FIELDS if k != "stockout_impacted"},
            "wave_id": wave_id,
            "stockout_impacted": int(row["stockout_impacted"]),
        }
    return normalized


def normalize_longest(rows: list[dict[str, str]]) -> dict[tuple[str, str, str], dict[str, object]]:
    normalized = {}
    for row in rows:
        wave_id = canonical_wave_id(row["wave_id"])
        key = (row["warehouse_id"], row["route_id"], row["business_date"])
        normalized[key] = {
            **{k: row[k] for k in ["warehouse_id", "route_id", "business_date"]},
            "wave_id": wave_id,
            "loaded_packages": int(row["loaded_packages"]),
            "wave_duration_minutes": int(row["wave_duration_minutes"]),
            "late_rate": f"{Decimal(row['late_rate']):.4f}",
            "stockout_exposure_minutes": int(row["stockout_exposure_minutes"]),
        }
    return normalized


def assert_outputs_match(data_dir: Path) -> None:
    expected_waves, expected_audit, expected_longest, expected_summary = compute_expected(data_dir)
    actual_wave_rows = read_answer_csv(ANSWER / "wave_metrics.csv")
    actual_longest_rows = read_answer_csv(ANSWER / "longest_wave_per_route.csv")
    actual_audit_rows = read_answer_tsv(ANSWER / "order_package_audit.tsv")

    assert actual_wave_rows and list(actual_wave_rows[0].keys()) == WAVE_FIELDS
    assert actual_longest_rows and list(actual_longest_rows[0].keys()) == LONGEST_FIELDS
    assert actual_audit_rows and list(actual_audit_rows[0].keys()) == AUDIT_FIELDS

    actual_waves = normalize_wave(actual_wave_rows)
    actual_audit = normalize_audit(actual_audit_rows)
    actual_longest = normalize_longest(actual_longest_rows)
    def stringify_keys(mapping):
        return {"::".join(map(str, key)): value for key, value in mapping.items()}

    assert actual_waves == expected_waves, json.dumps({"actual": stringify_keys(actual_waves), "expected": stringify_keys(expected_waves)}, indent=2, sort_keys=True, default=str)
    assert actual_audit == expected_audit, json.dumps({"actual": stringify_keys(actual_audit), "expected": stringify_keys(expected_audit)}, indent=2, sort_keys=True, default=str)
    assert actual_longest == expected_longest, json.dumps({"actual": stringify_keys(actual_longest), "expected": stringify_keys(expected_longest)}, indent=2, sort_keys=True, default=str)

    summary = json.loads((ANSWER / "data_quality_summary.json").read_text(encoding="utf-8"))
    for key, expected_value in expected_summary.items():
        assert summary.get(key) == expected_value, (key, summary, expected_summary)
    assert "timezone" in summary.get("timezone_handling", "").lower()
    assert "scan_id" in summary.get("deduplication_rules", "")


def test_main_outputs() -> None:
    run_pipeline()
    assert_outputs_match(DATA_DIR)


def copy_reference(target: Path, warehouses: list[dict[str, object]] | None = None) -> None:
    ref = target / "reference"
    ref.mkdir(parents=True, exist_ok=True)
    source_ref = DATA_DIR / "reference"
    shutil.copyfile(source_ref / "skus.csv", ref / "skus.csv")
    if warehouses is None:
        shutil.copyfile(source_ref / "route_sla.csv", ref / "route_sla.csv")
        shutil.copyfile(source_ref / "warehouses.csv", ref / "warehouses.csv")
    else:
        write_csv(ref / "warehouses.csv", ["warehouse_id", "region", "timezone"], warehouses)
        write_csv(
            ref / "route_sla.csv",
            ["warehouse_id", "route_id", "sla_minutes"],
            [{"warehouse_id": row["warehouse_id"], "route_id": "R1", "sla_minutes": 90} for row in warehouses],
        )


def make_case(rows: dict[str, list[dict[str, object]]]) -> Path:
    root = Path(tempfile.mkdtemp(prefix="clickhouse-wave-case-"))
    (root / "package_scans").mkdir(parents=True)
    (root / "order_events").mkdir(parents=True)
    (root / "inventory_snapshots").mkdir(parents=True)
    copy_reference(root, rows.get("warehouses"))
    write_csv(
        root / "package_scans" / "scans.csv.gz",
        ["scan_id", "package_id", "order_id", "warehouse_id", "route_id", "sku_id", "scan_type", "event_time", "ingested_at"],
        rows["scans"],
        gz=True,
    )
    write_jsonl_gz(root / "order_events" / "events.jsonl.gz", rows["orders"])
    write_csv(
        root / "inventory_snapshots" / "snapshots.csv.gz",
        ["snapshot_id", "warehouse_id", "sku_id", "available_to_promise", "event_time", "ingested_at"],
        rows["inventory"],
        gz=True,
    )
    return root


def test_guardrail_alternate_data_dirs() -> None:
    cases = [
        {
            "orders": [
                {"order_id": "G1", "status": "COMPLETED", "event_time": "2026-02-10 07:40:00", "event_version": 1, "ingested_at": "2026-02-10 07:40:01"},
                {"order_id": "G2", "status": "COMPLETED", "event_time": "2026-02-10 08:00:00", "event_version": 1, "ingested_at": "2026-02-10 08:00:01"},
                {"order_id": "G2", "status": "FRAUD_REJECTED", "event_time": "2026-02-10 08:00:00", "event_version": 2, "ingested_at": "2026-02-10 08:00:02"},
            ],
            "scans": [
                {"scan_id": "GS1", "package_id": "GP1", "order_id": "G1", "warehouse_id": "WH_SF", "route_id": "R1", "sku_id": "SKU_COFFEE", "scan_type": "LOADED_ON_TRUCK", "event_time": "2026-02-10 07:55:00", "ingested_at": "2026-02-10 07:55:01"},
                {"scan_id": "GS2", "package_id": "GP2", "order_id": "G2", "warehouse_id": "WH_SF", "route_id": "R1", "sku_id": "SKU_COFFEE", "scan_type": "LOADED_ON_TRUCK", "event_time": "2026-02-10 08:05:00", "ingested_at": "2026-02-10 08:05:01"},
                {"scan_id": "GD1", "package_id": "GP1", "order_id": "G1", "warehouse_id": "WH_SF", "route_id": "R1", "sku_id": "SKU_COFFEE", "scan_type": "DELIVERED", "event_time": "2026-02-10 09:40:00", "ingested_at": "2026-02-10 09:40:01"},
            ],
            "inventory": [
                {"snapshot_id": "GI1", "warehouse_id": "WH_SF", "sku_id": "SKU_COFFEE", "available_to_promise": 0, "event_time": "2026-02-10 07:30:00", "ingested_at": "2026-02-10 07:30:01"},
                {"snapshot_id": "GI2", "warehouse_id": "WH_SF", "sku_id": "SKU_COFFEE", "available_to_promise": 5, "event_time": "2026-02-10 08:10:00", "ingested_at": "2026-02-10 08:10:01"},
            ],
        },
        {
            "warehouses": [{"warehouse_id": "WH_CHI", "region": "central", "timezone": "America/Chicago"}],
            "orders": [
                {"order_id": "G3", "status": "COMPLETED", "event_time": "2026-11-01 06:20:00", "event_version": 1, "ingested_at": "2026-11-01 06:20:01"},
                {"order_id": "G4", "status": "COMPLETED", "event_time": "2026-11-01 06:30:00", "event_version": 1, "ingested_at": "2026-11-01 06:30:01"},
            ],
            "scans": [
                {"scan_id": "GS3", "package_id": "GP3", "order_id": "G3", "warehouse_id": "WH_CHI", "route_id": "R1", "sku_id": "SKU_TEA", "scan_type": "LOADED_ON_TRUCK", "event_time": "2026-11-01 06:40:00", "ingested_at": "2026-11-01 06:40:01"},
                {"scan_id": "GS4", "package_id": "GP4", "order_id": "G4", "warehouse_id": "WH_CHI", "route_id": "R1", "sku_id": "SKU_TEA", "scan_type": "LOADED_ON_TRUCK", "event_time": "2026-11-01 07:05:00", "ingested_at": "2026-11-01 07:05:01"},
                {"scan_id": "GD3", "package_id": "GP3", "order_id": "G3", "warehouse_id": "WH_CHI", "route_id": "R1", "sku_id": "SKU_TEA", "scan_type": "DELIVERED", "event_time": "2026-11-01 07:35:00", "ingested_at": "2026-11-01 07:35:01"},
            ],
            "inventory": [
                {"snapshot_id": "GI3", "warehouse_id": "WH_CHI", "sku_id": "SKU_TEA", "available_to_promise": 1, "event_time": "2026-11-01 06:00:00", "ingested_at": "2026-11-01 06:00:01"},
                {"snapshot_id": "GI4", "warehouse_id": "WH_CHI", "sku_id": "SKU_TEA", "available_to_promise": 0, "event_time": "2026-11-01 06:50:00", "ingested_at": "2026-11-01 06:50:01"},
                {"snapshot_id": "GI5", "warehouse_id": "WH_CHI", "sku_id": "SKU_TEA", "available_to_promise": 3, "event_time": "2026-11-01 07:20:00", "ingested_at": "2026-11-01 07:20:01"},
            ],
        },
        {
            "warehouses": [{"warehouse_id": "WH_TOK", "region": "apac", "timezone": "Asia/Tokyo"}],
            "orders": [
                {"order_id": "G5", "status": "COMPLETED", "event_time": "2026-02-11 14:50:00", "event_version": 1, "ingested_at": "2026-02-11 14:50:01"}
            ],
            "scans": [
                {"scan_id": "GS5", "package_id": "GP5", "order_id": "G5", "warehouse_id": "WH_TOK", "route_id": "R1", "sku_id": "SKU_BAG", "scan_type": "LOADED_ON_TRUCK", "event_time": "2026-02-11 15:05:00", "ingested_at": "2026-02-11 15:05:01"},
                {"scan_id": "GS5", "package_id": "GP5", "order_id": "G5", "warehouse_id": "WH_TOK", "route_id": "R1", "sku_id": "SKU_BAG", "scan_type": "LOADED_ON_TRUCK", "event_time": "2026-02-11 15:05:00", "ingested_at": "2026-02-11 15:05:05"},
            ],
            "inventory": [
                {"snapshot_id": "GI6", "warehouse_id": "WH_TOK", "sku_id": "SKU_BAG", "available_to_promise": 0, "event_time": "2026-02-11 14:55:00", "ingested_at": "2026-02-11 14:55:01"},
                {"snapshot_id": "GI7", "warehouse_id": "WH_TOK", "sku_id": "SKU_BAG", "available_to_promise": 4, "event_time": "2026-02-11 15:15:00", "ingested_at": "2026-02-11 15:15:01"},
            ],
        },
    ]
    for rows in cases:
        case_dir = make_case(rows)
        run_pipeline(case_dir)
        assert_outputs_match(case_dir)
    run_pipeline()


def test_clickhouse_contract_and_guardrails() -> None:
    assert Path("/root/.agents/skills/clickhouse-io/scripts/write_delivery_wave_sql.sh").is_file(), (
        "bound ClickHouse diagnostic scaffold is missing from the agent environment"
    )
    query = ["clickhouse-client", "--query"]
    assert int(run(query + ["SELECT count() FROM system.tables WHERE database='analytics' AND name='wave_metrics'"]).strip()) == 1
    assert int(run(query + ["SELECT count() FROM analytics.wave_metrics"]).strip()) >= 1
    assert int(run(query + ["SELECT count() FROM analytics.order_package_audit WHERE sla_status='MISSING_DELIVERY'"]).strip()) >= 0

    if Path("/opt/clickhouse-wave-data.sha256").exists():
        checksum = run(["bash", "-lc", "cd / && sha256sum -c /opt/clickhouse-wave-data.sha256"], timeout=60)
        assert "OK" in checksum

    source = RUNNER.read_text(encoding="utf-8", errors="replace") + "\n" + SQL_FILE.read_text(encoding="utf-8", errors="replace")
    sql_source = SQL_FILE.read_text(encoding="utf-8", errors="replace").lower()
    lowered = source.lower()
    forbidden = [
        "/tests",
        "/solution",
        "reward.txt",
        "pytest",
        "expected_",
        "zoneinfo",
        "python ",
        "python3 ",
        "pandas",
        "duckdb",
        "sqlite",
        "allow_nonconst_timezone_arguments",
        "system.time_zones",
        "create function",
        "user_scripts",
        "timezone_calendar",
        "numbers(1440",
        "numbers(2880",
    ]
    for token in forbidden:
        assert token not in lowered, f"pipeline source must not reference {token}"
    sql_forbidden = [
        "formatdatetime(",
        "parsedatetime",
        "fromunixtimestamp",
        "todate(formatdatetime",
        "substring(",
    ]
    for token in sql_forbidden:
        assert token not in sql_source, f"build_waves.sql must not use string-based timezone conversion: {token}"
    assert "delivery-wave-clickhouse-io-scaffold" in sql_source, "build_waves.sql should preserve the ClickHouse skill scaffold provenance marker"

    assert "loAded_on_truck".lower() in lowered
    assert "argmax" in lowered or "row_number" in lowered
    assert "laginframe" in lowered or "lag(" in lowered
    assert "totimezone" in lowered
    assert "dateDiff('minute'".lower() in lowered

    timezone_literals = set(re.findall(r"'((?:America|Europe|Asia)/[A-Za-z0-9_+/-]+)'", source))
    assert timezone_literals <= {
        "America/Los_Angeles",
        "America/New_York",
        "America/Chicago",
        "Europe/London",
        "Asia/Tokyo",
    }


if __name__ == "__main__":
    test_main_outputs()
    test_guardrail_alternate_data_dirs()
    test_clickhouse_contract_and_guardrails()
