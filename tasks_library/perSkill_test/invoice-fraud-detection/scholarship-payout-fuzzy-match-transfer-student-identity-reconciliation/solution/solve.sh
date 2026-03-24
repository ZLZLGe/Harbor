#!/bin/bash
set -e

python3 <<'PY'
import csv
import re
from difflib import SequenceMatcher
from itertools import permutations


def normalize_name(name):
    text = name.strip().lower()
    if "," in text:
        left, right = text.split(",", 1)
        text = f"{right} {left}"
    text = text.replace("-", " ").replace("'", " ")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return " ".join(text.split())


def token_score(token_a, token_b):
    if token_a == token_b:
        return 100.0
    if len(token_a) == 1 and token_b.startswith(token_a):
        return 92.0
    if len(token_b) == 1 and token_a.startswith(token_b):
        return 92.0
    return SequenceMatcher(None, token_a, token_b).ratio() * 100


def name_score(name_a, name_b):
    tokens_a = normalize_name(name_a).split()
    tokens_b = normalize_name(name_b).split()
    if not tokens_a or not tokens_b:
        return 0.0

    shorter, longer = (tokens_a, tokens_b) if len(tokens_a) <= len(tokens_b) else (tokens_b, tokens_a)
    best = 0.0
    for permutation in permutations(range(len(longer)), len(shorter)):
        scores = [token_score(shorter[i], longer[j]) for i, j in enumerate(permutation)]
        score = max(0.0, sum(scores) / len(shorter) - 6 * (len(longer) - len(shorter)))
        best = max(best, score)
    return round(best, 2)


def parse_amount(value):
    return float(value)


with open("/root/student_directory.csv", encoding="utf-8", newline="") as handle:
    students = list(csv.DictReader(handle))

with open("/root/scholarship_awards.csv", encoding="utf-8", newline="") as handle:
    awards = list(csv.DictReader(handle))

with open("/root/payout_batch.csv", encoding="utf-8", newline="") as handle:
    payouts = list(csv.DictReader(handle))

student_by_id = {student["student_id"]: student for student in students}
resolved_awards = []

for award in awards:
    student_scores = []
    for student in students:
        best_alias_score = max(
            name_score(award["listed_student_name"], student["official_name"]),
            name_score(award["listed_student_name"], student["preferred_name"]),
        )
        student_scores.append(
            {
                "student_id": student["student_id"],
                "student_name": student["official_name"],
                "score": best_alias_score,
            }
        )

    student_scores.sort(key=lambda item: item["score"], reverse=True)
    best = student_scores[0]
    second_score = student_scores[1]["score"] if len(student_scores) > 1 else 0.0
    is_reliable = best["score"] >= 88 and (best["score"] - second_score) >= 4

    resolved_awards.append(
        {
            **award,
            "approved_amount": parse_amount(award["approved_amount"]),
            "matched_student_id": best["student_id"] if is_reliable else "",
            "matched_student_name": best["student_name"] if is_reliable else "",
            "award_resolved": is_reliable,
        }
    )

exceptions = []
fieldnames = [
    "payment_id",
    "scholarship_code",
    "beneficiary_name",
    "matched_student_id",
    "matched_student_name",
    "destination_account",
    "paid_amount",
    "reason",
]

for payout in payouts:
    candidate_awards = []
    for award in resolved_awards:
        if award["scholarship_code"] != payout["scholarship_code"]:
            continue

        aliases = [award["listed_student_name"]]
        if award["award_resolved"]:
            student = student_by_id[award["matched_student_id"]]
            aliases.extend([student["official_name"], student["preferred_name"]])

        best_candidate_score = max(name_score(payout["beneficiary_name"], alias) for alias in aliases)
        candidate_awards.append({"score": best_candidate_score, "award": award})

    candidate_awards.sort(key=lambda item: item["score"], reverse=True)
    best_candidate = candidate_awards[0]
    second_candidate_score = candidate_awards[1]["score"] if len(candidate_awards) > 1 else 0.0
    payout_resolved = (
        best_candidate["score"] >= 88
        and (best_candidate["score"] - second_candidate_score) >= 4
        and best_candidate["award"]["award_resolved"]
    )

    matched_student_id = ""
    matched_student_name = ""
    reason = None

    if not payout_resolved:
        reason = "Unmatched Student"
    else:
        award = best_candidate["award"]
        matched_student_id = award["matched_student_id"]
        matched_student_name = award["matched_student_name"]
        student = student_by_id[matched_student_id]
        if payout["destination_account"] != student["registered_bank_account"]:
            reason = "Account Mismatch"
        elif abs(parse_amount(payout["paid_amount"]) - award["approved_amount"]) > 0.01:
            reason = "Amount Mismatch"

    if reason:
        exceptions.append(
            {
                "payment_id": payout["payment_id"],
                "scholarship_code": payout["scholarship_code"],
                "beneficiary_name": payout["beneficiary_name"],
                "matched_student_id": matched_student_id,
                "matched_student_name": matched_student_name,
                "destination_account": payout["destination_account"],
                "paid_amount": f"{parse_amount(payout['paid_amount']):.2f}",
                "reason": reason,
            }
        )

with open("/root/scholarship_exceptions.csv", "w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(exceptions)
PY
