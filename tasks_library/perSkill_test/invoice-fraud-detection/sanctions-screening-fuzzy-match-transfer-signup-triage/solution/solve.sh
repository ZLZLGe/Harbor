#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
import json
import re
from difflib import SequenceMatcher


INPUT_SIGNUPS = "/root/customer_signups.tsv"
INPUT_WATCHLIST = "/root/sanctions_watchlist.json"
OUTPUT_PATH = "/root/watchlist_hits.tsv"


def normalize_name(value):
    value = value.lower().replace("-", " ")
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    return " ".join(value.split())


def ratio(a, b):
    return SequenceMatcher(None, a, b).ratio()


def token_sort_ratio(a, b):
    return ratio(" ".join(sorted(a.split())), " ".join(sorted(b.split())))


def partial_ratio(a, b):
    if len(a) > len(b):
        a, b = b, a
    if not a:
        return 0.0
    best = 0.0
    width = len(a)
    for idx in range(len(b) - width + 1):
        best = max(best, ratio(a, b[idx:idx + width]))
    return best


def similarity(left, right):
    left = normalize_name(left)
    right = normalize_name(right)
    return max(ratio(left, right), token_sort_ratio(left, right), partial_ratio(left, right))


with open(INPUT_WATCHLIST, "r", encoding="utf-8") as handle:
    watchlist = json.load(handle)

with open(INPUT_SIGNUPS, "r", encoding="utf-8", newline="") as handle:
    signups = list(csv.DictReader(handle, delimiter="\t"))

results = []

for signup in signups:
    scored = []
    for entity in watchlist:
        names = [entity["primary_name"], *entity["aliases"]]
        best_score = max(similarity(signup["submitted_name"], candidate) for candidate in names)
        scored.append((best_score, entity))

    scored.sort(key=lambda item: item[0], reverse=True)
    best_score, best_entity = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else 0.0

    is_clear_match = best_score >= 0.86 and (best_score - second_score) >= 0.05
    if not is_clear_match:
        continue

    dob_match = signup["date_of_birth"] == best_entity["date_of_birth"]
    country_match = signup["country_code"] in best_entity["risk_countries"]
    if not dob_match and not country_match:
        continue

    if dob_match and country_match:
        match_basis = "DOB+Country"
    elif dob_match:
        match_basis = "DOB"
    else:
        match_basis = "Country"

    results.append(
        {
            "signup_id": signup["signup_id"],
            "submitted_name": signup["submitted_name"],
            "date_of_birth": signup["date_of_birth"],
            "country_code": signup["country_code"],
            "matched_entity_id": best_entity["entity_id"],
            "matched_name": best_entity["primary_name"],
            "match_basis": match_basis,
            "program": best_entity["program"],
        }
    )

results.sort(key=lambda row: row["signup_id"])

with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as handle:
    fieldnames = [
        "signup_id",
        "submitted_name",
        "date_of_birth",
        "country_code",
        "matched_entity_id",
        "matched_name",
        "match_basis",
        "program",
    ]
    writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(results)
PY
