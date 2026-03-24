#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import os
from datetime import date

ADVISORY_PATH = os.environ.get("ADVISORY_PATH", "/root/vendor_psirt_feed.json")
TICKET_PATH = os.environ.get("TICKET_PATH", "/root/remediation_tickets.json")
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "/root/psirt_sla_escalations.json")
SNAPSHOT_DATE = date.fromisoformat(os.environ.get("SNAPSHOT_DATE", "2026-03-20"))
CLOSED_STATUSES = {"resolved", "deployed"}


def select_score(vulnerability):
    cvss = vulnerability.get("cvss", {})
    for key, label in (("nvd", "NVD"), ("ghsa", "GHSA"), ("redhat", "RedHat")):
        source = cvss.get(key, {})
        score = source.get("v3_score")
        if score is not None:
            return float(score), label
    return None, "N/A"


with open(ADVISORY_PATH, "r", encoding="utf-8") as handle:
    advisory_feed = json.load(handle)

with open(TICKET_PATH, "r", encoding="utf-8") as handle:
    ticket_state = json.load(handle)

tickets_by_advisory = {
    ticket["advisory_id"]: ticket
    for ticket in ticket_state.get("tickets", [])
}

escalations = []

for advisory in advisory_feed.get("advisories", []):
    best_score = None
    best_vulnerability_id = "N/A"
    best_source = "N/A"

    for vulnerability in advisory.get("vulnerabilities", []):
        score, source = select_score(vulnerability)
        if score is None:
            continue
        if best_score is None or score > best_score:
            best_score = score
            best_vulnerability_id = vulnerability["vulnerability_id"]
            best_source = source

    ticket = tickets_by_advisory.get(advisory["advisory_id"])
    if ticket is None or best_score is None:
        continue

    due_date = date.fromisoformat(ticket["sla_due_date"])
    is_overdue = due_date < SNAPSHOT_DATE
    is_open = ticket["status"] not in CLOSED_STATUSES

    if best_score >= 7.0 and is_overdue and is_open:
        escalations.append(
            {
                "advisory_id": advisory["advisory_id"],
                "ticket_id": ticket["ticket_id"],
                "product": advisory["product"],
                "owner": ticket["owner"],
                "status": ticket["status"],
                "best_vulnerability_id": best_vulnerability_id,
                "best_cvss_score": best_score,
                "score_source": best_source,
                "sla_due_date": ticket["sla_due_date"],
                "days_overdue": (SNAPSHOT_DATE - due_date).days,
                "published_at": advisory["published_at"],
                "bulletin_url": advisory["bulletin_url"],
            }
        )

escalations.sort(key=lambda item: (-item["days_overdue"], item["advisory_id"]))

payload = {
    "generated_for_date": SNAPSHOT_DATE.isoformat(),
    "minimum_cvss_for_escalation": 7.0,
    "escalations": escalations,
}

with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2)
    handle.write("\n")
PY
