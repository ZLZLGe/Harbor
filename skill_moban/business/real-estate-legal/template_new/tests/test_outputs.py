import hashlib
import json
import math
import re
from pathlib import Path

import pytest


ROOT = Path(__import__("os").environ.get("TASK_ROOT", "/root"))
PACKET = ROOT / "input" / "auction_packet"
OUTPUT = ROOT / "output"
REPORT = OUTPUT / "due_diligence_report.json"
MEMO = OUTPUT / "due_diligence_memo.md"

EXPECTED_HASHES = {
    "courts/court_docket_export.csv": "323962f95f0550d99db5cad251fe69adf87b973d11b613dc1f61e2737a154f87",
    "documents/payoff_and_repair_notes.md": "1a9ec2ce5ebe2bd7ecee924f34670638cd15340a6b303b596c9d4cf1a6934d9e",
    "documents/recorder_records.csv": "d7e6a9ce9994398f1fb161a7e14ba05039ecb939472d006b3dff6734e00a3971",
    "documents/title_commitment_excerpt.md": "69787fa5eb6a866180d9e8144a66b215e23bfef1bd4f84a07f1fd5d163c38c8c",
    "hoa/hoa_balance_letter.md": "b0c4776b050c4a17b308195fefdd8a67d1f5b8bb7417c82f9516d5e71daed281",
    "jurisdiction_rules.yaml": "ff42a91c8778a33257cc59fb7fd4ba2442aaf4e287f696c913d0bcf76e3b6772",
    "ledger/claims_ledger.csv": "6057fee2631f302ed9790a915698e557f3e54703f64af1789e9724544463ae86",
    "manifest.json": "01cfbf8ead1b84d31f0a6df943e6191cd416962016b79f9452f8b1c22ee87ecb",
    "market/market_comps.csv": "9c22e78cc801c079ef49f0b51d5103f1da2f7178e090793a5283a5b71ccd31f4",
    "market/valuation_summary.json": "ccc061f9699c338d12abd956785d2832acb6bf2a1683e75b1188ffbdb1291796",
    "notices/trustee_sale_notices.md": "3872bfec86817b91cc871a12b3902b0544733cb2e7c90e5417d1edcb27e3dc88",
    "occupancy/occupancy_notes.md": "56e1aef2084750001f591a36a779f3238bc0faa9b13ce80667ff37d851d2124d",
    "tax/tax_statement.json": "f3c0ffc9f012edded92e18baff9d3e266f73d7aac6cb566f533e6d943d6549c0",
}

VALID_PRIORITIES = {"senior", "foreclosing", "junior", "unknown"}
VALID_TREATMENTS = {"survives_sale", "paid_from_sale", "extinguished_by_sale", "requires_counsel_review"}
VALID_SEVERITIES = {"low", "medium", "high", "blocker"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="session")
def report():
    assert REPORT.exists(), "Missing /root/output/due_diligence_report.json"
    try:
        data = json.loads(REPORT.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        pytest.fail(f"Report is not valid JSON: {exc}")
    return data


@pytest.fixture(scope="session")
def memo_text():
    assert MEMO.exists(), "Missing /root/output/due_diligence_memo.md"
    return MEMO.read_text(encoding="utf-8")


def norm(text):
    return re.sub(r"\s+", " ", str(text).lower()).strip()


def approx(actual, expected, tol=1.0):
    assert isinstance(actual, (int, float)), f"Expected numeric value near {expected}, got {actual!r}"
    assert abs(float(actual) - expected) <= tol, f"Expected {expected}, got {actual}"


def claim_matching(report, *needles):
    claims = report.get("claims", [])
    for claim in claims:
        hay = norm(" ".join(str(claim.get(k, "")) for k in ("claimant", "claim_type", "source_id", "reason")))
        if all(n.lower() in hay for n in needles):
            return claim
    pytest.fail(f"Missing claim matching {needles}")


def risks_matching(report, *needles):
    risks = report.get("risk_flags", [])
    hits = []
    for risk in risks:
        hay = norm(" ".join(str(risk.get(k, "")) for k in ("risk_type", "summary", "source_id", "recommended_action")))
        if all(n.lower() in hay for n in needles):
            hits.append(risk)
    assert hits, f"Missing risk matching {needles}"
    return hits


def test_input_packet_integrity():
    for rel, expected in EXPECTED_HASHES.items():
        path = PACKET / rel
        assert path.exists(), f"Input source missing: {rel}"
        assert sha256(path) == expected, f"Input source was modified: {rel}"


def test_output_files_and_schema(report):
    assert set(p.name for p in OUTPUT.iterdir()) >= {"due_diligence_report.json", "due_diligence_memo.md"}

    for section in [
        "property",
        "sale",
        "claims",
        "risk_flags",
        "valuation",
        "recommendation",
        "open_issues",
        "evidence_index",
    ]:
        assert section in report, f"Missing top-level section {section}"

    assert isinstance(report["claims"], list) and len(report["claims"]) >= 8
    assert isinstance(report["risk_flags"], list) and len(report["risk_flags"]) >= 5
    assert isinstance(report["evidence_index"], list) and len(report["evidence_index"]) >= 8

    for claim in report["claims"]:
        assert claim.get("priority") in VALID_PRIORITIES
        assert claim.get("treatment") in VALID_TREATMENTS
        assert claim.get("source_id")
        if claim.get("amount") is not None:
            assert isinstance(claim["amount"], (int, float)), "Money fields must be numeric, not strings"

    for risk in report["risk_flags"]:
        assert risk.get("severity") in VALID_SEVERITIES
        assert risk.get("source_id")
        assert risk.get("summary")


def test_property_and_sale_facts(report):
    prop = report["property"]
    sale = report["sale"]
    assert prop["case_id"] == "AZ-MARICOPA-TR-2026-0417-78"
    assert prop["parcel_id"] == "214-18-074"
    assert "11837 W Juniper Ridge" in prop["address"]
    assert prop["county"] == "Maricopa"
    assert prop["state"] == "AZ"
    assert "Keller" in prop["owner_or_borrower"]

    assert sale["sale_type"] == "nonjudicial trustee sale"
    assert "Sonoran Title Trustee" in sale["selling_authority"]
    assert sale["auction_date"] == "2026-05-07"
    assert sale["opening_bid"] == 398000
    assert sale["sale_status"] == "active"
    reason = norm(sale["status_reason"])
    assert "correct" in reason
    assert "cancel" in reason or "no cancellation" in reason


def test_claim_priority_and_treatment(report):
    foreclosing = claim_matching(report, "sonoran desert bank")
    assert foreclosing["priority"] == "foreclosing"
    assert foreclosing["treatment"] == "paid_from_sale"
    approx(foreclosing["amount"], 421380)

    tax = claim_matching(report, "maricopa", "tax")
    assert tax["priority"] == "senior"
    assert tax["treatment"] == "survives_sale"
    approx(tax["amount"], 8742.16, tol=0.01)

    city = claim_matching(report, "city of peoria")
    assert city["priority"] == "senior"
    assert city["treatment"] == "survives_sale"
    approx(city["amount"], 6850)

    hoa_super = claim_matching(report, "copper ridge", "super")
    assert hoa_super["priority"] == "senior"
    assert hoa_super["treatment"] == "survives_sale"
    approx(hoa_super["amount"], 1800)

    hoa_remainder_candidates = [
        c for c in report["claims"]
        if "copper ridge" in norm(c.get("claimant", ""))
        and c.get("priority") == "junior"
        and c.get("treatment") == "extinguished_by_sale"
        and c.get("amount") is not None
        and abs(float(c.get("amount")) - 5130) <= 1
    ]
    assert hoa_remainder_candidates, "Missing junior/extinguished HOA remainder of 5130"
    hoa_remainder = hoa_remainder_candidates[0]
    assert hoa_remainder["priority"] == "junior"
    assert hoa_remainder["treatment"] == "extinguished_by_sale"
    approx(hoa_remainder["amount"], 5130)

    irs = claim_matching(report, "internal revenue")
    assert irs["priority"] == "junior"
    assert irs["treatment"] == "extinguished_by_sale"
    approx(irs["amount"], 27940)

    judgment = claim_matching(report, "north valley")
    assert judgment["priority"] == "junior"
    assert judgment["treatment"] == "extinguished_by_sale"

    released = claim_matching(report, "desert tile")
    assert released["treatment"] == "extinguished_by_sale"
    assert "release" in norm(released.get("reason", ""))

    solar = claim_matching(report, "solarbright")
    assert solar["priority"] in {"junior", "unknown"}
    assert solar["treatment"] == "requires_counsel_review"
    assert solar["amount"] is None


def test_risk_flags_are_material_and_nuanced(report):
    bankruptcy = risks_matching(report, "bankruptcy")[0]
    assert bankruptcy["severity"] in {"low", "medium"}
    assert "dismiss" in norm(bankruptcy["summary"])
    bankruptcy_summary = norm(bankruptcy["summary"])
    assert (
        "active stay" not in bankruptcy_summary
        or "no active stay" in bankruptcy_summary
        or "does not show an active stay" in bankruptcy_summary
        or "not show an active stay" in bankruptcy_summary
    )

    tenant = risks_matching(report, "tenant")[0]
    assert tenant["severity"] in {"medium", "high"}
    assert "2026-07-31" in tenant["summary"] or "forcible" in norm(tenant["summary"])

    irs = risks_matching(report, "irs")[0]
    assert irs["severity"] in {"medium", "high"}
    assert "redemption" in norm(irs["summary"] + " " + irs["recommended_action"])

    notice_candidates = [
        r for r in report["risk_flags"]
        if r.get("source_id") == "NOTICE-2026-0318"
        and any(word in norm(r.get("risk_type", "") + " " + r.get("summary", "")) for word in ["notice", "apn", "parcel", "correct"])
    ]
    assert notice_candidates, "Missing corrected notice/APN risk grounded in NOTICE-2026-0318"
    notice = notice_candidates[0]
    assert notice["severity"] in {"low", "medium"}
    assert "correct" in norm(notice["summary"])

    solar_mentions = [
        norm(r.get("summary", "") + " " + r.get("recommended_action"))
        for r in report["risk_flags"]
        if "solar" in norm(r.get("risk_type", "") + " " + r.get("summary", "") + " " + r.get("recommended_action"))
    ]
    solar_mentions += [
        norm(i.get("issue", "") + " " + i.get("why_it_matters", "") + " " + i.get("next_step", ""))
        for i in report.get("open_issues", [])
        if "solar" in norm(i.get("issue", "") + " " + i.get("why_it_matters", "") + " " + i.get("next_step", ""))
    ]
    solar_text = " ".join(solar_mentions + [norm(" ".join(report["recommendation"].get("conditions_before_bid", [])))])
    assert "solar" in solar_text, "Solar fixture/payoff uncertainty must be covered as a risk, condition, or open issue"
    assert any(word in solar_text for word in ["payoff", "lease", "fixture", "counsel", "equipment"])


def test_valuation_math(report):
    val = report["valuation"]
    expected = {
        "as_is_value_low": 610000,
        "as_is_value_high": 650000,
        "arv_mid": 710000,
        "repair_reserve": 38000,
        "eviction_reserve": 9500,
        "closing_cost_reserve": 18000,
        "surviving_debt_total": 17392.16,
        "recommended_max_bid": 414100,
    }
    for key, value in expected.items():
        approx(val[key], value, tol=0.01 if isinstance(value, float) else 1)

    recomputed = min(
        val["as_is_value_low"] * 0.80,
        val["arv_mid"] * 0.70
        - val["repair_reserve"]
        - val["eviction_reserve"]
        - val["closing_cost_reserve"]
        - val["surviving_debt_total"],
    )
    recomputed = math.floor(recomputed / 100) * 100
    assert val["recommended_max_bid"] == recomputed
    assert val["recommended_max_bid"] > report["sale"]["opening_bid"]


def test_recommendation_logic(report):
    rec = report["recommendation"]
    assert rec["decision"] == "BID_WITH_CONDITIONS"
    joined = norm(" ".join(rec.get("primary_reasons", []) + rec.get("conditions_before_bid", [])))
    for keyword in ["bankruptcy", "hoa", "possession", "solar"]:
        assert keyword in joined
    assert "irs" in joined or ("federal" in joined and "redemption" in joined)


def test_evidence_index_and_source_grounding(report):
    known_source_ids = {
        "MANIFEST",
        "COST-2026-0418",
        "NOTICE-2026-0129",
        "NOTICE-2026-0318",
        "REC-2018-0714472",
        "REC-2019-0441821",
        "REC-2020-0031188",
        "REC-2021-0983104",
        "REC-2023-0654407",
        "REC-2024-0517720",
        "REC-2025-0040191",
        "REC-2025-0892218",
        "REC-2025-0937712",
        "REC-2026-0188842",
        "TAX-2025-7781",
        "HOA-2026-0416",
        "COURT-BK-25-11988",
        "COURT-FC-25-09214",
        "COURT-CV-24-04402",
        "COURT-LL-26-00177",
        "OCC-2026-0415",
        "VALUE-2026-0419",
        "COMP-001",
        "COMP-002",
        "COMP-003",
        "COMP-004",
    }
    evidence_ids = {e.get("source_id") for e in report["evidence_index"]}
    assert {"NOTICE-2026-0318", "TAX-2025-7781", "HOA-2026-0416", "OCC-2026-0415", "VALUE-2026-0419"} <= evidence_ids

    for item in report["claims"] + report["risk_flags"]:
        assert item["source_id"] in known_source_ids, f"Fabricated or ungrounded source_id: {item['source_id']}"

    for evidence in report["evidence_index"]:
        assert evidence.get("source_id")
        assert evidence.get("source_location")
        loc = str(evidence.get("source_location"))
        assert loc.startswith("/root/input/auction_packet/") or loc == "/root/input/auction_packet/manifest.json"
        assert evidence.get("supports")


def test_memo_consistency_and_no_verifier_hack(report, memo_text):
    lower = memo_text.lower()
    for heading in [
        "property",
        "sale status",
        "lien and title summary",
        "risk flags",
        "valuation",
        "recommendation",
        "open issues",
    ]:
        assert heading in lower, f"Memo missing section heading: {heading}"

    assert "bid_with_conditions" in lower
    assert "414100" in lower
    assert "17392.16" in lower
    assert "214-18-074" in memo_text
    assert "SolarBright" in memo_text

    combined = json.dumps(report).lower() + "\n" + lower
    forbidden = ["test_outputs.py", "pytest", "reward.txt", "verifier", "hidden answer", "/tests/"]
    for token in forbidden:
        assert token not in combined, f"Output appears to reference verifier internals: {token}"

    assert len(re.findall(r"\b(disclaimer|not legal advice)\b", lower)) <= 1, "Memo should not be a generic disclaimer-only response"
