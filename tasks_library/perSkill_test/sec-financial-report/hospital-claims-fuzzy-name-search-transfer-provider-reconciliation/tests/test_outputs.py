import json
import os

OUTPUT_FILE = "/root/claims_reconciliation.json"

EXPECTED = {
    "anchor_provider_search_term": "st mary med ctr westlk",
    "resolved_anchor_provider": {
        "provider_id": "PRV-1001",
        "provider_name": "Saint Mary Medical Center - Westlake",
        "network_id": "NET-ALPHA",
        "network_name": "NorthEast Care Alliance",
    },
    "resolved_high_cost_drugs": [
        {
            "search_term": "keytrudaa",
            "drug_code": "DRUG-9271",
            "canonical_name": "pembrolizumab 100 mg vial",
            "brand_name": "Keytruda",
        },
        {
            "search_term": "nivolimab",
            "drug_code": "DRUG-9299",
            "canonical_name": "nivolumab 40 mg/4 mL",
            "brand_name": "Opdivo",
        },
        {
            "search_term": "herzumaa",
            "drug_code": "DRUG-5117",
            "canonical_name": "trastuzumab-dkst 420 mg",
            "brand_name": "Herzuma",
        },
    ],
    "network_metrics": {
        "network_id": "NET-ALPHA",
        "network_name": "NorthEast Care Alliance",
        "high_cost_claim_count": 7,
        "denied_high_cost_claim_count": 2,
        "denial_rate": 0.285714,
        "high_cost_paid_amount": 209500.0,
    },
    "anomalous_claims": [
        {
            "claim_id": "C-10005",
            "provider_id": "PRV-1002",
            "provider_name": "Saint Mary Outpatient Infusion Pavilion",
            "drug_code": "DRUG-5117",
            "canonical_name": "trastuzumab-dkst 420 mg",
            "status": "DENIED",
            "allowed_amount": 85000.0,
            "paid_amount": 0.0,
            "reference_paid_amount": 82800.0,
            "anomaly_reason": "denied_high_cost_over_50000",
        },
        {
            "claim_id": "C-10007",
            "provider_id": "PRV-1001",
            "provider_name": "Saint Mary Medical Center - Westlake",
            "drug_code": "DRUG-9271",
            "canonical_name": "pembrolizumab 100 mg vial",
            "status": "PAID",
            "allowed_amount": 60000.0,
            "paid_amount": 59000.0,
            "reference_paid_amount": 42400.0,
            "anomaly_reason": "paid_above_reference_125pct",
        },
    ],
}


def load_output():
    assert os.path.isfile(OUTPUT_FILE), f"missing output file: {OUTPUT_FILE}"
    with open(OUTPUT_FILE) as f:
        return json.load(f)


def test_exact_output():
    data = load_output()
    assert data["anchor_provider_search_term"] == EXPECTED["anchor_provider_search_term"]
    assert data["resolved_anchor_provider"] == EXPECTED["resolved_anchor_provider"]
    assert data["resolved_high_cost_drugs"] == EXPECTED["resolved_high_cost_drugs"]
    assert data["network_metrics"] == EXPECTED["network_metrics"]
    assert data["anomalous_claims"] == EXPECTED["anomalous_claims"]


def test_consistency():
    data = load_output()
    metrics = data["network_metrics"]
    assert metrics["denial_rate"] == round(
        metrics["denied_high_cost_claim_count"] / metrics["high_cost_claim_count"], 6
    )

    anomalies = data["anomalous_claims"]
    assert [item["claim_id"] for item in anomalies] == sorted(
        item["claim_id"] for item in anomalies
    )
    for item in anomalies:
        assert isinstance(item["allowed_amount"], (int, float))
        assert isinstance(item["paid_amount"], (int, float))
        assert isinstance(item["reference_paid_amount"], (int, float))
        if item["status"] == "DENIED":
            assert item["allowed_amount"] >= 50000
            assert item["anomaly_reason"] == "denied_high_cost_over_50000"
        else:
            assert item["paid_amount"] > item["reference_paid_amount"] * 1.25
            assert item["anomaly_reason"] == "paid_above_reference_125pct"
