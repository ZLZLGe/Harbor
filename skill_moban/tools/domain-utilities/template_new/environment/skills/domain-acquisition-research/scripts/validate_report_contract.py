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
REPORT_PATH = Path("/app/output/opportunity_report.json")
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
            stdout=open("/tmp/domain-skill-validate.log", "a", encoding="utf-8"),
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


def read_csv_index(path: Path, key: str) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return {row[key]: row for row in csv.DictReader(handle)}


def archive_band(domain: str) -> str:
    text = (DATA_ROOT / "archive_summaries" / f"{domain}.md").read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("Relevance band: "):
            return line.split(": ", 1)[1].strip()
    raise RuntimeError(f"Missing archive band for {domain}")


def snapshot(domain: str) -> dict[str, object]:
    ensure_service()
    response = requests.get(f"{SNAPSHOT_URL}/snapshots/{domain}", timeout=10)
    response.raise_for_status()
    return response.json()


def expected_reason_codes(
    domain: str,
    report_row: dict[str, object],
    authority_index: dict[str, dict[str, str]],
) -> list[str]:
    codes: list[str] = []
    market_fit = float(report_row["market_fit_score"])
    authority_score = float(report_row["authority_score"])
    legal_risk = float(report_row["legal_risk_score"])
    price_ceiling = report_row["price_ceiling_usd"]
    band = archive_band(domain)
    snap = snapshot(domain)
    type_in = int(authority_index[domain]["type_in_score"])

    if market_fit >= 50:
        codes.append("STRONG_MARKET_FIT")
    if authority_score >= 30:
        codes.append("HIGH_TRUST_SIGNALS")
    if band in {"strong", "medium"}:
        codes.append("ARCHIVE_TOPIC_MATCH")
    elif band == "weak":
        codes.append("WEAK_ARCHIVE_RELEVANCE")
    else:
        codes.append("ARCHIVE_MISMATCH")
    if legal_risk >= 20:
        codes.append("TRADEMARK_COLLISION")
    elif legal_risk > 0:
        codes.append("SIMILARITY_WARNING")
    if price_ceiling is not None:
        if float(snap["asking_price_usd"]) <= float(price_ceiling):
            codes.append("PRICE_WITHIN_CEILING")
        else:
            codes.append("ASKING_PRICE_ABOVE_CEILING")
    if type_in >= 7:
        codes.append("TYPE_IN_POTENTIAL")
    if str(snap["landing_style"]) == "parked":
        codes.append("PARKED_LANDING")
    return codes


def canonical_evidence_pairs() -> set[tuple[str, str]]:
    return {
        ("candidate_domains.csv", "keyword_alignment"),
        ("authority_metrics.csv", "referring_domains"),
        ("local_snapshot_api", "listing_state"),
    }


def main() -> None:
    if not REPORT_PATH.exists():
        raise SystemExit("Missing /app/output/opportunity_report.json")

    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    authority_index = read_csv_index(DATA_ROOT / "authority_metrics.csv", "domain")

    failures: list[str] = []
    for row in report.get("evaluations", []):
        domain = row["domain"]
        actual_codes = set(row.get("reason_codes", []))
        expected_codes = expected_reason_codes(domain, row, authority_index)
        for code in expected_codes:
            if code not in actual_codes:
                failures.append(f"{domain}: missing reason code {code}")

        evidence_pairs = {(item.get("source"), item.get("key")) for item in row.get("evidence", [])}
        for pair in canonical_evidence_pairs():
            if pair not in evidence_pairs:
                failures.append(f"{domain}: missing evidence anchor {pair[0]} / {pair[1]}")

    if failures:
        print("Report contract check failed:")
        for item in failures:
            print(f"- {item}")
        raise SystemExit(1)

    print("Report contract check passed.")


if __name__ == "__main__":
    main()
