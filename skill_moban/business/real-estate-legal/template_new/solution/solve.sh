#!/usr/bin/env bash
set -euo pipefail

ROOT="${TASK_ROOT:-/root}"
OUT="$ROOT/output"
mkdir -p "$OUT"

python3 - <<'PY'
import json
import os
from pathlib import Path

root = Path(os.environ.get("TASK_ROOT", "/root"))
out = root / "output"
out.mkdir(parents=True, exist_ok=True)

report = {
    "property": {
        "case_id": "AZ-MARICOPA-TR-2026-0417-78",
        "parcel_id": "214-18-074",
        "address": "11837 W Juniper Ridge Dr, Peoria, AZ 85383",
        "county": "Maricopa",
        "state": "AZ",
        "owner_or_borrower": "Evan M. Keller and Priya S. Keller",
    },
    "sale": {
        "sale_type": "nonjudicial trustee sale",
        "selling_authority": "Sonoran Title Trustee Services LLC",
        "auction_date": "2026-05-07",
        "opening_bid": 398000,
        "sale_status": "active",
        "status_reason": "Corrective notice NOTICE-2026-0318 fixed the parcel number to 214-18-074, continued the sale to 2026-05-07, and states no cancellation as of 2026-04-20; the recent bankruptcy case was dismissed.",
    },
    "claims": [
        {
            "claimant": "Sonoran Desert Bank",
            "claim_type": "foreclosing deed of trust",
            "source_id": "REC-2019-0441821",
            "recorded_date": "2019-06-14",
            "amount": 421380,
            "priority": "foreclosing",
            "treatment": "paid_from_sale",
            "reason": "This is the foreclosing instrument identified in the manifest and local rule file.",
        },
        {
            "claimant": "Maricopa County Treasurer",
            "claim_type": "delinquent property tax",
            "source_id": "TAX-2025-7781",
            "recorded_date": "2025-12-31",
            "amount": 8742.16,
            "priority": "senior",
            "treatment": "survives_sale",
            "reason": "The local rules state delinquent county property taxes survive the trustee sale.",
        },
        {
            "claimant": "Copper Ridge Community Association",
            "claim_type": "hoa superpriority regular assessments",
            "source_id": "HOA-2026-0416",
            "recorded_date": "2023-10-18",
            "amount": 1800,
            "priority": "senior",
            "treatment": "survives_sale",
            "reason": "The local rules give six months of regular HOA assessments superpriority treatment.",
        },
        {
            "claimant": "Copper Ridge Community Association",
            "claim_type": "hoa non-superpriority balance",
            "source_id": "REC-2023-0654407",
            "recorded_date": "2023-10-18",
            "amount": 5130,
            "priority": "junior",
            "treatment": "extinguished_by_sale",
            "reason": "The remaining older assessments, late fees, collection costs, and attorney fees are not given superpriority in the local rule file.",
        },
        {
            "claimant": "City of Peoria",
            "claim_type": "municipal nuisance and water assessment",
            "source_id": "REC-2025-0937712",
            "recorded_date": "2025-12-03",
            "amount": 6850,
            "priority": "senior",
            "treatment": "survives_sale",
            "reason": "The local rules state municipal assessment charges survive unless released.",
        },
        {
            "claimant": "Internal Revenue Service",
            "claim_type": "federal tax lien",
            "source_id": "REC-2024-0517720",
            "recorded_date": "2024-08-12",
            "amount": 27940,
            "priority": "junior",
            "treatment": "extinguished_by_sale",
            "reason": "The lien is junior to the foreclosing deed of trust and the trustee packet includes an IRS notice certificate.",
        },
        {
            "claimant": "North Valley Credit Partners",
            "claim_type": "judgment lien",
            "source_id": "REC-2025-0040191",
            "recorded_date": "2025-01-17",
            "amount": 18500,
            "priority": "junior",
            "treatment": "extinguished_by_sale",
            "reason": "The judgment lien was recorded after the foreclosing instrument and no special priority rule applies.",
        },
        {
            "claimant": "Desert Tile Supply",
            "claim_type": "released mechanics lien",
            "source_id": "REC-2018-0714472",
            "recorded_date": "2018-10-03",
            "amount": 14200,
            "priority": "senior",
            "treatment": "extinguished_by_sale",
            "reason": "Although recorded before the deed of trust, it was fully released by REC-2020-0031188 and should not be counted as surviving debt.",
        },
        {
            "claimant": "SolarBright Leasing LLC",
            "claim_type": "fixture filing for leased solar equipment",
            "source_id": "REC-2021-0983104",
            "recorded_date": "2021-12-21",
            "amount": None,
            "priority": "unknown",
            "treatment": "requires_counsel_review",
            "reason": "The recorder export gives no payoff demand or sale-treatment details for the leased rooftop equipment.",
        },
    ],
    "risk_flags": [
        {
            "risk_type": "recent bankruptcy",
            "severity": "medium",
            "source_id": "COURT-BK-25-11988",
            "summary": "A Chapter 13 case was filed on 2025-11-20 but dismissed on 2026-02-28, so no active stay appears in the packet.",
            "recommended_action": "Confirm no reinstatement or new bankruptcy filing before bidding.",
        },
        {
            "risk_type": "tenant possession",
            "severity": "high",
            "source_id": "OCC-2026-0415",
            "summary": "The property appears occupied and an occupant claims a lease through 2026-07-31, with a pending forcible detainer case.",
            "recommended_action": "Budget for possession delay and verify lease priority with counsel.",
        },
        {
            "risk_type": "irs redemption period",
            "severity": "medium",
            "source_id": "REC-2024-0517720",
            "summary": "The IRS lien appears junior and noticed, but the local rules require disclosure of possible post-sale redemption risk.",
            "recommended_action": "Confirm IRS notice compliance and redemption timing before resale planning.",
        },
        {
            "risk_type": "municipal and code condition",
            "severity": "medium",
            "source_id": "REC-2025-0937712",
            "summary": "A municipal nuisance and water assessment survives, and site notes mention an unpermitted rear patio enclosure.",
            "recommended_action": "Carry the municipal assessment and permit-cure risk in bid economics.",
        },
        {
            "risk_type": "corrected notice",
            "severity": "low",
            "source_id": "NOTICE-2026-0318",
            "summary": "The initial trustee notice transposed the parcel suffix, but a corrective notice recorded the correct parcel and continued sale date.",
            "recommended_action": "Confirm no later objection to the corrective notice before bidding.",
        },
        {
            "risk_type": "leased solar equipment",
            "severity": "medium",
            "source_id": "REC-2021-0983104",
            "summary": "A fixture filing identifies leased rooftop solar equipment without a payoff demand.",
            "recommended_action": "Request lease/payoff documents and counsel review before treating the equipment as free and clear.",
        },
    ],
    "valuation": {
        "as_is_value_low": 610000,
        "as_is_value_high": 650000,
        "arv_mid": 710000,
        "repair_reserve": 38000,
        "eviction_reserve": 9500,
        "closing_cost_reserve": 18000,
        "surviving_debt_total": 17392.16,
        "recommended_max_bid": 414100,
    },
    "recommendation": {
        "decision": "BID_WITH_CONDITIONS",
        "primary_reasons": [
            "The corrected sale notice supports an active 2026-05-07 sale and the opening bid is below the calculated maximum bid.",
            "Known surviving tax, HOA superpriority, and municipal charges total 17392.16.",
            "Possession, IRS redemption timing, and leased solar equipment require pre-bid confirmation.",
        ],
        "conditions_before_bid": [
            "Confirm no new bankruptcy or sale cancellation immediately before auction.",
            "Confirm IRS notice compliance and redemption timeline.",
            "Obtain HOA payoff confirmation separating superpriority and junior amounts.",
            "Plan for tenant possession and the pending forcible detainer case.",
            "Review SolarBright lease or payoff documents with counsel.",
        ],
    },
    "open_issues": [
        {
            "issue": "SolarBright leased equipment payoff and sale treatment are missing.",
            "why_it_matters": "The fixture filing may affect equipment rights or buyer obligations after sale.",
            "next_step": "Request the solar lease and payoff demand before bidding.",
        },
        {
            "issue": "Occupant claims a lease through 2026-07-31.",
            "why_it_matters": "Possession delay can affect holding costs and resale timing.",
            "next_step": "Have counsel evaluate lease priority and forcible-detainer strategy.",
        },
        {
            "issue": "IRS redemption timing should be confirmed.",
            "why_it_matters": "Even if the lien payment claim is extinguished, redemption risk can affect resale timing.",
            "next_step": "Verify IRS notice certificate and redemption period before resale planning.",
        },
    ],
    "evidence_index": [
        {"source_id": "MANIFEST", "source_location": "/root/input/auction_packet/manifest.json", "supports": "Target property and sale metadata."},
        {"source_id": "REC-2019-0441821", "source_location": "/root/input/auction_packet/documents/recorder_records.csv", "supports": "Foreclosing deed of trust."},
        {"source_id": "NOTICE-2026-0318", "source_location": "/root/input/auction_packet/notices/trustee_sale_notices.md", "supports": "Corrected parcel number, continued sale date, and active sale status."},
        {"source_id": "TAX-2025-7781", "source_location": "/root/input/auction_packet/tax/tax_statement.json", "supports": "Delinquent property tax amount."},
        {"source_id": "HOA-2026-0416", "source_location": "/root/input/auction_packet/hoa/hoa_balance_letter.md", "supports": "HOA superpriority allocation."},
        {"source_id": "REC-2025-0937712", "source_location": "/root/input/auction_packet/documents/recorder_records.csv", "supports": "Municipal assessment."},
        {"source_id": "COURT-BK-25-11988", "source_location": "/root/input/auction_packet/courts/court_docket_export.csv", "supports": "Dismissed bankruptcy docket."},
        {"source_id": "OCC-2026-0415", "source_location": "/root/input/auction_packet/occupancy/occupancy_notes.md", "supports": "Occupancy and tenant claim."},
        {"source_id": "VALUE-2026-0419", "source_location": "/root/input/auction_packet/market/valuation_summary.json", "supports": "Valuation range and ARV."},
        {"source_id": "COST-2026-0418", "source_location": "/root/input/auction_packet/documents/payoff_and_repair_notes.md", "supports": "Repair, eviction, and closing reserves."},
    ],
}

(out / "due_diligence_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

memo = f"""# Property

11837 W Juniper Ridge Dr, Peoria, AZ 85383; parcel 214-18-074; borrower/owner Evan M. Keller and Priya S. Keller.

# Sale Status

The trustee sale is active for 2026-05-07 with an opening bid of 398000. NOTICE-2026-0318 corrected the initial parcel-number error, and the recent bankruptcy case was dismissed rather than active.

# Lien and Title Summary

The foreclosing deed of trust is REC-2019-0441821. Known surviving claims are Maricopa County property taxes of 8742.16, the HOA six-month superpriority amount of 1800, and the City of Peoria municipal assessment of 6850. The IRS lien and judgment lien appear junior and extinguished by the sale, but IRS redemption timing remains a condition. The released mechanics lien should not be counted as surviving debt.

# Risk Flags

Material risks are tenant possession, recent dismissed bankruptcy, IRS redemption timing, municipal/code condition issues, the corrected notice history, and the SolarBright leased-equipment filing with missing payoff information.

# Valuation

As-is value low is 610000, as-is value high is 650000, and ARV midpoint is 710000. Reserves are 38000 for repairs, 9500 for eviction/possession, and 18000 for closing/carry/resale costs. Known surviving debt is 17392.16, producing a recommended maximum bid of 414100.

# Recommendation

BID_WITH_CONDITIONS. The economics support bidding above the opening bid, but the investor should confirm no new bankruptcy or cancellation, verify IRS notice and redemption timing, confirm HOA payoff allocation, plan for possession, and review the SolarBright lease or payoff documents.

# Open Issues

SolarBright payoff and sale treatment are missing. The occupant claims a lease through 2026-07-31. IRS redemption timing should be confirmed before resale planning.
"""
(out / "due_diligence_memo.md").write_text(memo, encoding="utf-8")
PY
