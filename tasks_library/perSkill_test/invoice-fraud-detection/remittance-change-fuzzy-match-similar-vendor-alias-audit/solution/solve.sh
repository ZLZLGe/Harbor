#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
import json
import re
from difflib import SequenceMatcher


OUTPUT_PATH = "/root/remittance_alerts.json"
MASTER_PATH = "/root/vendor_master.csv"
REQUEST_PATH = "/root/remittance_requests.json"

TOKEN_CANONICAL = {
    "incorporated": "inc",
    "inc": "inc",
    "corporation": "corp",
    "corp": "corp",
    "company": "co",
    "co": "co",
    "limited": "ltd",
    "ltd": "ltd",
    "international": "intl",
    "intl": "intl",
    "medical": "medical",
    "med": "medical",
    "services": "services",
    "svc": "services",
    "manufacturing": "mfg",
    "mfg": "mfg",
    "industrial": "industrial",
    "indl": "industrial",
    "equipment": "equipment",
    "equip": "equipment",
}


def normalize(name):
    lowered = name.lower()
    lowered = re.sub(r"[^a-z0-9\\s]", " ", lowered)
    tokens = [TOKEN_CANONICAL.get(token, token) for token in lowered.split()]
    tokens.sort()
    return " ".join(tokens)


with open(MASTER_PATH, newline="", encoding="utf-8") as handle:
    vendors = list(csv.DictReader(handle))

with open(REQUEST_PATH, encoding="utf-8") as handle:
    requests = json.load(handle)

normalized_vendors = []
for vendor in vendors:
    normalized_vendors.append(
        {
            "vendor_id": vendor["vendor_id"],
            "legal_name": vendor["legal_name"],
            "approved_bank_account": vendor["approved_bank_account"],
            "tax_id": vendor["tax_id"],
            "normalized_name": normalize(vendor["legal_name"]),
        }
    )

alerts = []

for request in requests:
    normalized_request_name = normalize(request["submitted_vendor_name"])
    scored_candidates = []

    for vendor in normalized_vendors:
        score = SequenceMatcher(None, normalized_request_name, vendor["normalized_name"]).ratio() * 100
        scored_candidates.append((score, vendor))

    scored_candidates.sort(key=lambda item: item[0], reverse=True)
    best_score, best_vendor = scored_candidates[0]
    second_score = scored_candidates[1][0] if len(scored_candidates) > 1 else 0

    if best_score < 90 or best_score - second_score < 4:
        alerts.append(
            {
                "request_id": request["request_id"],
                "submitted_vendor_name": request["submitted_vendor_name"],
                "matched_vendor_id": None,
                "matched_vendor_name": None,
                "proposed_bank_account": request["proposed_bank_account"],
                "proposed_tax_id": request["proposed_tax_id"],
                "reason": "Unmatched Vendor",
            }
        )
        continue

    if request["proposed_bank_account"] != best_vendor["approved_bank_account"]:
        alerts.append(
            {
                "request_id": request["request_id"],
                "submitted_vendor_name": request["submitted_vendor_name"],
                "matched_vendor_id": best_vendor["vendor_id"],
                "matched_vendor_name": best_vendor["legal_name"],
                "proposed_bank_account": request["proposed_bank_account"],
                "proposed_tax_id": request["proposed_tax_id"],
                "reason": "Bank Account Conflict",
            }
        )
        continue

    if request["proposed_tax_id"] != best_vendor["tax_id"]:
        alerts.append(
            {
                "request_id": request["request_id"],
                "submitted_vendor_name": request["submitted_vendor_name"],
                "matched_vendor_id": best_vendor["vendor_id"],
                "matched_vendor_name": best_vendor["legal_name"],
                "proposed_bank_account": request["proposed_bank_account"],
                "proposed_tax_id": request["proposed_tax_id"],
                "reason": "Tax ID Conflict",
            }
        )

with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
    json.dump(alerts, handle, indent=2)
PY
