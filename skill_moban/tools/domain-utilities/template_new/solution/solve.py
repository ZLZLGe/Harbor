#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from statistics import median
import subprocess
import sys
import time

import requests


DATA_ROOT = Path(os.environ.get("DATA_ROOT", "/app/data"))
OUTPUT_PATH = Path(
    os.environ.get("OUTPUT_PATH", os.environ.get("PRIMARY_OUTPUT_PATH", "/app/output/opportunity_report.json"))
)
SERVICE_URL = os.environ.get("DOMAIN_SNAPSHOT_URL", "http://127.0.0.1:8331")
SERVER_PATH = Path(
    os.environ.get("DOMAIN_SNAPSHOT_SERVER_PATH", "/services/domain-audit/server.py")
)


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_archive_summary(domain: str) -> dict[str, str]:
    text = (DATA_ROOT / "archive_summaries" / f"{domain}.md").read_text(encoding="utf-8")
    result = {}
    for line in text.splitlines():
        if ": " in line:
            key, value = line.split(": ", 1)
            result[key.strip()] = value.strip()
    return result


def archive_bonus(band: str) -> int:
    return {"strong": 12, "medium": 7, "weak": 2, "mismatch": -4}[band]


def liquidity_bonus(state: str) -> int:
    return {"fixed-price": 8, "make-offer": 6, "brokered": 4, "parked": 2}[state]


def landing_bonus(style: str) -> int:
    return {
        "operator-marketplace": 6,
        "lead-gen": 5,
        "brandable-inventory": 4,
        "parked": 1,
    }[style]


def liquidity_multiplier(state: str) -> float:
    return {"fixed-price": 1.03, "make-offer": 1.00, "brokered": 0.96, "parked": 0.80}[state]


def archive_discount(band: str) -> float:
    return {"strong": 1.00, "medium": 0.92, "weak": 0.80, "mismatch": 0.55}[band]


def as_bool(value: str) -> bool:
    return value.lower() == "true"


def round2(value: float) -> float:
    return round(float(value), 2)


def reason_codes(
    market_fit: float,
    authority_score: float,
    archive_band: str,
    legal_risk: float,
    asking_price: float,
    price_ceiling: float | None,
    type_in_score: int,
    landing_style: str,
) -> list[str]:
    codes: list[str] = []
    if market_fit >= 50:
        codes.append("STRONG_MARKET_FIT")
    if authority_score >= 30:
        codes.append("HIGH_TRUST_SIGNALS")
    if archive_band in {"strong", "medium"}:
        codes.append("ARCHIVE_TOPIC_MATCH")
    elif archive_band == "weak":
        codes.append("WEAK_ARCHIVE_RELEVANCE")
    else:
        codes.append("ARCHIVE_MISMATCH")
    if legal_risk >= 20:
        codes.append("TRADEMARK_COLLISION")
    elif legal_risk > 0:
        codes.append("SIMILARITY_WARNING")
    if price_ceiling is not None:
        if asking_price <= price_ceiling:
            codes.append("PRICE_WITHIN_CEILING")
        else:
            codes.append("ASKING_PRICE_ABOVE_CEILING")
    if type_in_score >= 7:
        codes.append("TYPE_IN_POTENTIAL")
    if landing_style == "parked":
        codes.append("PARKED_LANDING")
    return codes


def fetch_snapshots() -> dict[str, dict[str, object]]:
    ensure_snapshot_service()
    manifest = requests.get(f"{SERVICE_URL}/manifest", timeout=10).json()
    result = {}
    for domain in manifest["candidates"]:
        result[domain] = requests.get(f"{SERVICE_URL}/snapshots/{domain}", timeout=10).json()
    return result


def ensure_snapshot_service() -> None:
    try:
        response = requests.get(f"{SERVICE_URL}/health", timeout=2)
        if response.ok:
            return
    except requests.RequestException:
        pass

    if SERVER_PATH.exists():
        subprocess.Popen(
            [sys.executable, str(SERVER_PATH)],
            stdout=open("/tmp/domain-snapshot-solution.log", "a", encoding="utf-8"),
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            response = requests.get(f"{SERVICE_URL}/health", timeout=2)
            if response.ok:
                return
        except requests.RequestException:
            time.sleep(0.5)
    raise RuntimeError("domain snapshot service did not become healthy")


def main() -> None:
    candidates = sorted(load_csv(DATA_ROOT / "candidate_domains.csv"), key=lambda row: row["domain"])
    authority_index = {row["domain"]: row for row in load_csv(DATA_ROOT / "authority_metrics.csv")}
    legal_index = {row["domain"]: row for row in load_csv(DATA_ROOT / "trademark_flags.csv")}
    sales_index: dict[str, list[float]] = {}
    for row in load_csv(DATA_ROOT / "sales_comps.csv"):
        sales_index.setdefault(row["comp_family"], []).append(float(row["sale_price_usd"]))
    snapshots = fetch_snapshots()

    evaluations = []
    for row in candidates:
        authority = authority_index[row["domain"]]
        legal = legal_index[row["domain"]]
        snapshot = snapshots[row["domain"]]
        archive = load_archive_summary(row["domain"])
        archive_band = archive["Relevance band"]

        market_fit = (
            int(row["keyword_alignment"])
            + int(row["tone_fit"])
            + int(row["memorability"])
            + int(row["brevity_bonus"])
        )
        authority_score = (
            min(float(authority["referring_domains"]) / 5.0, 18.0)
            + float(authority["trust_signal_score"])
            + float(authority["continuity_bonus"])
            + float(archive_bonus(archive_band))
            - float(authority["link_risk_penalty"])
        )
        commercial = (
            int(row["buyer_intent_score"])
            + int(authority["type_in_score"])
            + liquidity_bonus(str(snapshot["listing_state"]))
            + landing_bonus(str(snapshot["landing_style"]))
        )
        legal_risk = (
            int(legal["exact_mark_hits"]) * 16
            + int(legal["similarity_hits"]) * 8
            + int(legal["restricted_term_hits"]) * 5
            + (6 if as_bool(legal["confusion_flag"]) else 0)
        )
        total_score = market_fit + authority_score + commercial - legal_risk

        comp_median = median(sales_index[row["comp_family"]])
        ceiling = (
            comp_median
            * (0.65 + market_fit / 180.0)
            * (0.72 + authority_score / 220.0)
            * liquidity_multiplier(str(snapshot["listing_state"]))
            * max(0.50, 1.0 - legal_risk / 100.0)
            * archive_discount(archive_band)
        )

        if (
            legal_risk >= 20
            or archive_band == "mismatch"
            or str(snapshot["rdap_status"]) != "registered"
            or total_score < 75
        ):
            status = "reject"
            price_ceiling = None
        elif (
            total_score >= 100
            and legal_risk <= 18
            and float(snapshot["asking_price_usd"]) <= ceiling
            and archive_band in {"strong", "medium"}
        ):
            status = "buy_now"
            price_ceiling = round2(ceiling)
        else:
            status = "monitor"
            price_ceiling = round2(ceiling)

        evaluations.append(
            {
                "domain": row["domain"],
                "status": status,
                "market_fit_score": round2(market_fit),
                "authority_score": round2(authority_score),
                "commercial_intent_score": round2(commercial),
                "legal_risk_score": round2(legal_risk),
                "price_ceiling_usd": price_ceiling,
                "total_score": round2(total_score),
                "reason_codes": reason_codes(
                    market_fit,
                    authority_score,
                    archive_band,
                    legal_risk,
                    float(snapshot["asking_price_usd"]),
                    price_ceiling,
                    int(authority["type_in_score"]),
                    str(snapshot["landing_style"]),
                ),
                "evidence": [
                    {
                        "source": "candidate_domains.csv",
                        "key": "keyword_alignment",
                        "value": row["keyword_alignment"],
                    },
                    {
                        "source": "authority_metrics.csv",
                        "key": "referring_domains",
                        "value": authority["referring_domains"],
                    },
                    {
                        "source": "local_snapshot_api",
                        "key": "listing_state",
                        "value": str(snapshot["listing_state"]),
                    },
                    {
                        "source": "trademark_flags.csv",
                        "key": "risk_summary",
                        "value": legal["risk_summary"],
                    },
                ],
            }
        )

    evaluations = sorted(evaluations, key=lambda row: row["domain"])
    buy_now = sorted(
        [row for row in evaluations if row["status"] == "buy_now"],
        key=lambda row: (-float(row["total_score"]), row["domain"]),
    )
    report = {
        "segment": "field-service-dispatch-intelligence",
        "top_pick": buy_now[0]["domain"],
        "buy_now_ranked": [row["domain"] for row in buy_now[:3]],
        "evaluations": evaluations,
    }
    OUTPUT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
