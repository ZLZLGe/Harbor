#!/bin/bash

python3 - <<'PY'
import json
import os
import re
from difflib import SequenceMatcher

import pandas as pd


root_dir = os.environ.get("TASK_ROOT", "/root")

providers = pd.read_csv(f"{root_dir}/provider_master.csv")
drugs = pd.read_csv(f"{root_dir}/drug_catalog.csv")
claims = pd.read_csv(f"{root_dir}/medical_claims.csv")


def normalize(text):
    return re.sub(r"[^a-z0-9]+", "", str(text).lower())


def score(term, candidate):
    return SequenceMatcher(None, normalize(term), normalize(candidate)).ratio()


def best_provider_row(term):
    best_index = None
    best_score = -1.0
    for index, row in providers.iterrows():
        candidate_score = max(
            score(term, row["provider_name"]),
            score(term, f"{row['provider_name']} {row['city']}"),
        )
        if candidate_score > best_score:
            best_index = index
            best_score = candidate_score
    return providers.loc[best_index]


def best_drug_row(term):
    best_index = None
    best_score = -1.0
    for index, row in drugs.iterrows():
        candidate_score = max(
            score(term, row["canonical_name"]),
            score(term, row["brand_name"]),
            score(term, f"{row['canonical_name']} {row['brand_name']}"),
        )
        if candidate_score > best_score:
            best_index = index
            best_score = candidate_score
    return drugs.loc[best_index]


anchor_search_term = "st mary med ctr westlk"
anchor_provider = best_provider_row(anchor_search_term)

drug_search_terms = ["keytrudaa", "nivolimab", "herzumaa"]
resolved_high_cost_drugs = []
for term in drug_search_terms:
    match = best_drug_row(term)
    resolved_high_cost_drugs.append(
        {
            "search_term": term,
            "drug_code": match["drug_code"],
            "canonical_name": match["canonical_name"],
            "brand_name": match["brand_name"],
        }
    )

monitored_codes = {item["drug_code"] for item in resolved_high_cost_drugs}

claims["provider_id"] = claims["provider_name_raw"].apply(
    lambda value: best_provider_row(value)["provider_id"]
)
claims["drug_code"] = claims["drug_name_raw"].apply(
    lambda value: best_drug_row(value)["drug_code"]
)

claims = claims.merge(
    providers[["provider_id", "provider_name", "network_id", "network_name"]],
    on="provider_id",
    how="left",
).merge(
    drugs[["drug_code", "canonical_name", "brand_name", "reference_unit_paid_amount"]],
    on="drug_code",
    how="left",
)

filtered_claims = claims[
    (claims["network_id"] == anchor_provider["network_id"])
    & (claims["drug_code"].isin(monitored_codes))
].copy()
filtered_claims["reference_paid_amount"] = (
    filtered_claims["units"] * filtered_claims["reference_unit_paid_amount"]
)

anomalous_claims = filtered_claims[
    (
        (filtered_claims["status"] == "DENIED")
        & (filtered_claims["allowed_amount"] >= 50000)
    )
    | (
        (filtered_claims["status"] == "PAID")
        & (
            filtered_claims["paid_amount"]
            > filtered_claims["reference_paid_amount"] * 1.25
        )
    )
].copy()
anomalous_claims["anomaly_reason"] = anomalous_claims["status"].map(
    {
        "DENIED": "denied_high_cost_over_50000",
        "PAID": "paid_above_reference_125pct",
    }
)
anomalous_claims = anomalous_claims.sort_values("claim_id")

output = {
    "anchor_provider_search_term": anchor_search_term,
    "resolved_anchor_provider": {
        "provider_id": anchor_provider["provider_id"],
        "provider_name": anchor_provider["provider_name"],
        "network_id": anchor_provider["network_id"],
        "network_name": anchor_provider["network_name"],
    },
    "resolved_high_cost_drugs": resolved_high_cost_drugs,
    "network_metrics": {
        "network_id": anchor_provider["network_id"],
        "network_name": anchor_provider["network_name"],
        "high_cost_claim_count": int(len(filtered_claims)),
        "denied_high_cost_claim_count": int(
            (filtered_claims["status"] == "DENIED").sum()
        ),
        "denial_rate": round(
            (filtered_claims["status"] == "DENIED").sum() / len(filtered_claims), 6
        ),
        "high_cost_paid_amount": float(filtered_claims["paid_amount"].sum()),
    },
    "anomalous_claims": [
        {
            "claim_id": row["claim_id"],
            "provider_id": row["provider_id"],
            "provider_name": row["provider_name"],
            "drug_code": row["drug_code"],
            "canonical_name": row["canonical_name"],
            "status": row["status"],
            "allowed_amount": float(row["allowed_amount"]),
            "paid_amount": float(row["paid_amount"]),
            "reference_paid_amount": float(row["reference_paid_amount"]),
            "anomaly_reason": row["anomaly_reason"],
        }
        for _, row in anomalous_claims.iterrows()
    ],
}

with open(f"{root_dir}/claims_reconciliation.json", "w") as f:
    json.dump(output, f, indent=2)
PY
