#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
import json
import re
from difflib import SequenceMatcher


OUTPUT_PATH = "/root/provider_claim_blocks.json"
CLAIMS_PATH = "/root/provider_claims.json"
REGISTRY_PATH = "/root/authorized_clinic_registry.tsv"

TOKEN_CANONICAL = {
    "ctr": "center",
    "center": "center",
    "med": "medicine",
    "medical": "medicine",
    "medicine": "medicine",
    "assoc": "associates",
    "associates": "associates",
    "grp": "group",
    "group": "group",
    "diag": "diagnostics",
    "diagnostics": "diagnostics",
    "peds": "pediatrics",
    "pediatrics": "pediatrics",
    "women": "womens",
    "womens": "womens",
}
DROP_TOKENS = {"llc", "pllc", "pc"}


def normalize_name(name):
    text = name.lower().replace("women's", "womens")
    text = re.sub(r"[^a-z0-9\\s]", " ", text)
    tokens = []
    for token in text.split():
        if token in DROP_TOKENS:
            continue
        tokens.append(TOKEN_CANONICAL.get(token, token))
    tokens.sort()
    return " ".join(tokens)


def similarity_score(name_a, name_b):
    return SequenceMatcher(None, normalize_name(name_a), normalize_name(name_b)).ratio() * 100


with open(REGISTRY_PATH, encoding="utf-8", newline="") as handle:
    registry_rows = list(csv.DictReader(handle, delimiter="\t"))

with open(CLAIMS_PATH, encoding="utf-8") as handle:
    claims = json.load(handle)

flagged_claims = []

for claim in claims:
    candidates = []
    for row in registry_rows:
        candidates.append(
            {
                "score": similarity_score(claim["submitted_clinic_name"], row["legal_name"]),
                "row": row,
            }
        )

    candidates.sort(key=lambda item: item["score"], reverse=True)
    best = candidates[0]
    second_score = candidates[1]["score"] if len(candidates) > 1 else 0.0

    matched_registry_id = None
    matched_clinic_name = None
    reason = None

    if best["score"] < 88 or (best["score"] - second_score) < 3:
        reason = "Unmatched Clinic"
    else:
        matched_registry_id = best["row"]["registry_id"]
        matched_clinic_name = best["row"]["legal_name"]
        if claim["billed_npi"] != best["row"]["authorized_npi"]:
            reason = "NPI Mismatch"
        elif claim["service_state"] != best["row"]["state"]:
            reason = "State Mismatch"
        elif claim["settlement_account"] != best["row"]["settlement_account"]:
            reason = "Settlement Account Mismatch"

    if reason is None:
        continue

    flagged_claims.append(
        {
            "claim_id": claim["claim_id"],
            "submitted_clinic_name": claim["submitted_clinic_name"],
            "matched_registry_id": matched_registry_id,
            "matched_clinic_name": matched_clinic_name,
            "billed_npi": claim["billed_npi"],
            "service_state": claim["service_state"],
            "settlement_account": claim["settlement_account"],
            "reason": reason,
        }
    )

with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
    json.dump(flagged_claims, handle, indent=2)
PY
