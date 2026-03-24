#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
import json
import os
import re
from difflib import SequenceMatcher


REQUESTS_PATH = os.environ.get("PAYMENT_REQUESTS_PATH", "/root/payment_requests.csv")
LEDGER_PATH = os.environ.get("APPROVED_VENDOR_LEDGER_PATH", "/root/approved_vendor_ledger.json")
PO_PATH = os.environ.get("PURCHASE_ORDERS_PATH", "/root/purchase_orders.csv")
OUTPUT_PATH = os.environ.get("PRIMARY_OUTPUT_FILE", "/root/payment_anomalies.json")
MATCH_THRESHOLD = 85


def normalize_vendor_name(text: str) -> str:
    lowered = text.lower().strip()
    lowered = lowered.replace("&", " and ")
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    tokens = []
    replacements = {
        "ltd": "ltd",
        "limited": "ltd",
        "inc": "inc",
        "incorporated": "inc",
        "co": "company",
        "company": "company",
        "corp": "corp",
        "corporation": "corp",
        "grp": "group",
        "llc": "llc",
    }
    for token in lowered.split():
        tokens.append(replacements.get(token, token))
    return " ".join(tokens)


def similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, left, right).ratio() * 100


with open(LEDGER_PATH, "r", encoding="utf-8") as handle:
    vendors = json.load(handle)

with open(PO_PATH, "r", encoding="utf-8", newline="") as handle:
    po_rows = list(csv.DictReader(handle))

with open(REQUESTS_PATH, "r", encoding="utf-8", newline="") as handle:
    request_rows = list(csv.DictReader(handle))

po_by_number = {row["po_number"]: row for row in po_rows}
vendor_choices = []

for vendor in vendors:
    normalized_name = normalize_vendor_name(vendor["vendor_name"])
    vendor_choices.append((normalized_name, vendor))

anomalies = []

for row in request_rows:
    raw_vendor_name = row["submitted_vendor_name"]
    normalized_request_name = normalize_vendor_name(raw_vendor_name)
    matched_vendor = None
    best_score = -1.0

    for normalized_vendor_name, vendor in vendor_choices:
        score = similarity(normalized_request_name, normalized_vendor_name)
        if score > best_score:
            best_score = score
            matched_vendor = vendor

    if best_score < MATCH_THRESHOLD:
        matched_vendor = None

    po_number = row["po_number"].strip() or None
    requested_amount = float(row["requested_amount"])

    def add_anomaly(reason: str) -> None:
        anomalies.append(
            {
                "request_id": row["request_id"],
                "vendor_name": raw_vendor_name,
                "requested_amount": requested_amount,
                "bank_account": row["bank_account"],
                "po_number": po_number,
                "reason": reason,
            }
        )

    if matched_vendor is None:
        add_anomaly("Unknown Vendor")
        continue

    if row["bank_account"] != matched_vendor["authorized_bank_account"]:
        add_anomaly("Bank Account Mismatch")
        continue

    if po_number is None or po_number not in po_by_number:
        add_anomaly("Invalid PO")
        continue

    po_record = po_by_number[po_number]

    if abs(requested_amount - float(po_record["approved_amount"])) > 0.01:
        add_anomaly("Amount Mismatch")
        continue

    if po_record["vendor_id"] != matched_vendor["vendor_id"]:
        add_anomaly("Vendor Mismatch")

with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
    json.dump(anomalies, handle, indent=2)
PY
