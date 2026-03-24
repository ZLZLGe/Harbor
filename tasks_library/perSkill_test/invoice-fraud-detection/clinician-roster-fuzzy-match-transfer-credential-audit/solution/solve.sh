#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
import re
from datetime import date
from difflib import SequenceMatcher


OUTPUT_PATH = "/root/license_exceptions.csv"


def normalize_name(text):
    text = text.lower()
    text = re.sub(r"\b(dr|rn|md|pa|pa-c|np|lpn|rt)\b", " ", text)
    text = text.replace("'", "")
    text = re.sub(r"\bdelacruz\b", "de la cruz", text)
    text = re.sub(r"\boconnor\b", "o connor", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def surname_forms(tokens):
    if not tokens:
        return set()

    forms = {tokens[-1], "".join(tokens)}
    if len(tokens) >= 2:
        forms.add(" ".join(tokens[-2:]))
        forms.add("".join(tokens[-2:]))
    if len(tokens) >= 3:
        forms.add(" ".join(tokens[-3:]))
        forms.add("".join(tokens[-3:]))
    return forms


def initials_score(alias_tokens, candidate_tokens):
    if not alias_tokens or not candidate_tokens:
        return 0.0

    if not surname_forms(alias_tokens).intersection(surname_forms(candidate_tokens)):
        return 0.0

    alias_given = alias_tokens[:-1]
    candidate_given = candidate_tokens[:-1]
    if not alias_given:
        return 0.85

    matched = 0
    for alias_token in alias_given:
        for candidate_token in candidate_given:
            if len(alias_token) == 1 and candidate_token.startswith(alias_token):
                matched += 1
                break
            if len(alias_token) > 1 and (
                candidate_token.startswith(alias_token) or alias_token.startswith(candidate_token)
            ):
                matched += 1
                break
    return matched / len(alias_given)


def score_name(alias, candidate):
    normalized_alias = normalize_name(alias)
    normalized_candidate = normalize_name(candidate)

    alias_sorted = " ".join(sorted(normalized_alias.split()))
    candidate_sorted = " ".join(sorted(normalized_candidate.split()))
    alias_compact = normalized_alias.replace(" ", "")
    candidate_compact = normalized_candidate.replace(" ", "")

    base_score = max(
        SequenceMatcher(None, normalized_alias, normalized_candidate).ratio(),
        SequenceMatcher(None, alias_sorted, candidate_sorted).ratio(),
        SequenceMatcher(None, alias_compact, candidate_compact).ratio(),
    )

    compatible_initials = initials_score(normalized_alias.split(), normalized_candidate.split())
    if compatible_initials:
        base_score = max(base_score, 0.72 + 0.25 * compatible_initials)

    return base_score


with open("/root/licensing_registry.csv", "r", encoding="utf-8", newline="") as handle:
    registry_rows = list(csv.DictReader(handle))

with open("/root/shift_roster.csv", "r", encoding="utf-8", newline="") as handle:
    roster_rows = list(csv.DictReader(handle))

exceptions = []

for row in roster_rows:
    best_match = None
    best_score = -1.0
    for candidate in registry_rows:
        current_score = score_name(row["clinician_alias"], candidate["full_name"])
        if current_score > best_score:
            best_score = current_score
            best_match = candidate

    reason = None
    matched_license_number = ""
    matched_registry_name = ""

    if best_match is None or best_score < 0.82:
        reason = "Unresolved Clinician"
    else:
        matched_license_number = best_match["license_number"]
        matched_registry_name = best_match["full_name"]

        if row["reported_license_number"] != best_match["license_number"]:
            reason = "License Number Mismatch"
        elif row["required_credential"] != best_match["credential_level"]:
            reason = "Credential Mismatch"
        elif best_match["status"] != "Active":
            reason = "Inactive License"
        elif date.fromisoformat(best_match["expires_on"]) < date.fromisoformat(row["shift_date"]):
            reason = "Expired License"

    if reason:
        exceptions.append(
            {
                "assignment_id": row["assignment_id"],
                "shift_date": row["shift_date"],
                "unit": row["unit"],
                "clinician_alias": row["clinician_alias"],
                "reported_license_number": row["reported_license_number"],
                "matched_license_number": matched_license_number,
                "matched_registry_name": matched_registry_name,
                "reason": reason,
            }
        )

exceptions.sort(key=lambda item: item["assignment_id"])

with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=[
            "assignment_id",
            "shift_date",
            "unit",
            "clinician_alias",
            "reported_license_number",
            "matched_license_number",
            "matched_registry_name",
            "reason",
        ],
    )
    writer.writeheader()
    writer.writerows(exceptions)
PY
