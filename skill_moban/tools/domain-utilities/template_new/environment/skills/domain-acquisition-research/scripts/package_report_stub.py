#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests


DATA_ROOT = Path("/app/data")
SNAPSHOT_URL = os.environ.get("DOMAIN_SNAPSHOT_URL", "http://127.0.0.1:8331")
SERVER_PATH = Path(
    os.environ.get("DOMAIN_SNAPSHOT_SERVER_PATH", "/services/domain-audit/server.py")
)


def ensure_service() -> None:
    try:
        response = requests.get(f"{SNAPSHOT_URL}/health", timeout=2)
        if response.ok:
            return
    except requests.RequestException:
        pass

    if SERVER_PATH.exists():
        subprocess.Popen(
            [sys.executable, str(SERVER_PATH)],
            stdout=open("/tmp/domain-skill-package.log", "a", encoding="utf-8"),
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            response = requests.get(f"{SNAPSHOT_URL}/health", timeout=2)
            if response.ok:
                return
        except requests.RequestException:
            time.sleep(0.5)
    raise RuntimeError("domain snapshot service did not become healthy")


def archive_band(domain: str) -> str:
    text = (DATA_ROOT / "archive_summaries" / f"{domain}.md").read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("Relevance band: "):
            return line.split(": ", 1)[1].strip()
    raise RuntimeError(f"Missing archive band for {domain}")


def type_in_score(domain: str) -> int:
    with (DATA_ROOT / "authority_metrics.csv").open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["domain"] == domain:
                return int(row["type_in_score"])
    raise RuntimeError(f"Missing authority row for {domain}")


def snapshot(domain: str) -> dict[str, object]:
    ensure_service()
    response = requests.get(f"{SNAPSHOT_URL}/snapshots/{domain}", timeout=10)
    response.raise_for_status()
    return response.json()


def main() -> None:
    report_path = Path("/app/output/opportunity_report.json")
    if not report_path.exists():
        raise SystemExit("Missing /app/output/opportunity_report.json")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    canonical_evidence = {
        domain_row["domain"]: [
            {"source": "candidate_domains.csv", "key": "keyword_alignment"},
            {"source": "authority_metrics.csv", "key": "referring_domains"},
            {"source": "local_snapshot_api", "key": "listing_state"},
            {"source": "trademark_flags.csv", "key": "risk_summary"},
        ]
        for domain_row in report.get("evaluations", [])
    }
    canonical_reason_codes = {}
    for row in report.get("evaluations", []):
        codes = []
        if float(row["market_fit_score"]) >= 50:
            codes.append("STRONG_MARKET_FIT")
        if float(row["authority_score"]) >= 30:
            codes.append("HIGH_TRUST_SIGNALS")
        band = archive_band(row["domain"])
        snap = snapshot(row["domain"])
        if band in {"strong", "medium"}:
            codes.append("ARCHIVE_TOPIC_MATCH")
        elif band == "weak":
            codes.append("WEAK_ARCHIVE_RELEVANCE")
        else:
            codes.append("ARCHIVE_MISMATCH")
        if float(row["legal_risk_score"]) >= 20:
            codes.append("TRADEMARK_COLLISION")
        elif float(row["legal_risk_score"]) > 0:
            codes.append("SIMILARITY_WARNING")
        if row["price_ceiling_usd"] is not None:
            codes.append(
                "PRICE_WITHIN_CEILING"
                if float(snap["asking_price_usd"]) <= float(row["price_ceiling_usd"])
                else "ASKING_PRICE_ABOVE_CEILING"
            )
        if type_in_score(row["domain"]) >= 7:
            codes.append("TYPE_IN_POTENTIAL")
        if str(snap["landing_style"]) == "parked":
            codes.append("PARKED_LANDING")
        canonical_reason_codes[row["domain"]] = codes
    print(
        json.dumps(
            {
                "segment": report.get("segment"),
                "top_pick": report.get("top_pick"),
                "buy_now_count": len(report.get("buy_now_ranked", [])),
                "evaluation_count": len(report.get("evaluations", [])),
                "canonical_evidence_fields": canonical_evidence,
                "canonical_reason_codes": canonical_reason_codes,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
