#!/bin/bash
set -e

python3 <<'PY'
import csv
import json
import re
from difflib import SequenceMatcher


LISTINGS_PATH = "/root/marketplace_listings.jsonl"
CATALOG_PATH = "/root/restricted_catalog.csv"
OUTPUT_PATH = "/root/restricted_listing_matches.json"
MATCH_THRESHOLD = 0.78
AMBIGUITY_GAP = 0.04

REPLACEMENTS = {
    "sat phone": "satellite phone",
    "satphone": "satellite phone",
    "derma pen": "dermapen",
    "microneedle": "microneedling",
    "rngr": "ranger",
    " av ": " aviation ",
    " det ": " detector ",
    "smooth beam": "smoothbeam",
}

NOISE_TOKENS = {
    "w",
    "with",
    "wall",
    "charger",
    "bundle",
    "combo",
    "sealed",
    "new",
    "open",
    "box",
    "case",
    "pouch",
}


def normalize(text):
    value = f" {text.lower()} "
    value = value.replace("&", " and ").replace("/", " ")
    for old, new in REPLACEMENTS.items():
        value = value.replace(old, new)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    tokens = [token for token in value.split() if token not in NOISE_TOKENS]
    return " ".join(tokens)


def sorted_ratio(left, right):
    left_sorted = " ".join(sorted(left.split()))
    right_sorted = " ".join(sorted(right.split()))
    return SequenceMatcher(None, left_sorted, right_sorted).ratio()


def partial_ratio(left, right):
    short, long = (left, right) if len(left) <= len(right) else (right, left)
    if not short:
        return 0.0
    best = 0.0
    for index in range(len(long) - len(short) + 1):
        window = long[index : index + len(short)]
        best = max(best, SequenceMatcher(None, short, window).ratio())
    return best


def score_match(left, right):
    return 0.7 * sorted_ratio(left, right) + 0.3 * partial_ratio(left, right)


with open(CATALOG_PATH, "r", encoding="utf-8", newline="") as handle:
    catalog_rows = list(csv.DictReader(handle))

catalog_entries = []
for row in catalog_rows:
    catalog_entries.append(
        {
            "catalog_id": row["catalog_id"],
            "canonical_title": row["canonical_title"],
            "restriction_reason": row["restriction_reason"],
            "normalized_title": normalize(row["canonical_title"]),
        }
    )

matches = []
with open(LISTINGS_PATH, "r", encoding="utf-8") as handle:
    for line in handle:
        listing = json.loads(line)
        normalized_title = normalize(listing["title"])
        scored_candidates = []

        for entry in catalog_entries:
            score = score_match(normalized_title, entry["normalized_title"])
            scored_candidates.append((score, entry["catalog_id"], entry))

        scored_candidates.sort(reverse=True)
        best_score, _, best_entry = scored_candidates[0]
        second_score = scored_candidates[1][0] if len(scored_candidates) > 1 else 0.0

        if best_score < MATCH_THRESHOLD:
            continue
        if best_score - second_score < AMBIGUITY_GAP:
            continue

        matches.append(
            {
                "listing_id": listing["listing_id"],
                "seller_id": listing["seller_id"],
                "listing_title": listing["title"],
                "matched_catalog_id": best_entry["catalog_id"],
                "matched_canonical_title": best_entry["canonical_title"],
                "restriction_reason": best_entry["restriction_reason"],
            }
        )

matches.sort(key=lambda item: item["listing_id"])

with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
    json.dump(matches, handle, indent=2)
PY
