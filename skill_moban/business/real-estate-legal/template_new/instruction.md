You are a real estate legal analyst preparing a pre-bid diligence summary for a trustee-sale auction. The investor needs to decide whether this property is safe to bid on, which liens or legal issues may survive the sale, and the maximum bid they should consider.

The available data files are in `/root/input/auction_packet/` as your input. The packet contains trustee sale notices, deed and lien records, court docket exports, tax and HOA balance records, occupancy notes, repair estimates, market comparable sales, and local foreclosure rules.

Your task:

1. Identify the target property, borrower or owner, parcel number, county, trustee or selling authority, auction date, sale status, and opening bid.

2. Reconstruct the relevant title and lien history. For each monetary claim, determine:
   - claimant
   - claim type
   - recorded date
   - amount
   - whether it is senior, foreclosing, junior, or unknown relative to the foreclosing instrument
   - whether it survives the sale, is paid from sale proceeds, is extinguished by the sale, or requires counsel review

3. Apply the local foreclosure and lien-priority rules in `/root/input/auction_packet/jurisdiction_rules.yaml`. Do not rely on generic foreclosure assumptions when the local rule file gives a specific rule.

4. Check for legal or possession risks, including bankruptcy, court stays, lis pendens, probate, divorce, tax issues, HOA enforcement, code violations, tenant or occupant claims, sale postponement, cancellation, and notice defects.

5. Estimate investor economics using the supplied lien records, tax records, repair notes, occupancy records, and market comparable records.

   Calculate:

   `recommended_max_bid = floor_to_nearest_100(min(as_is_value_low * 0.80, arv_mid * 0.70 - repair_reserve - eviction_reserve - closing_cost_reserve - surviving_debt_total))`

6. Make a final recommendation:
   - `BID`
   - `BID_WITH_CONDITIONS`
   - `DO_NOT_BID`

   Use `DO_NOT_BID` if there is an active bankruptcy stay, cancelled sale, missing authority to sell, unresolved blocker risk, or unknown senior/surviving debt that could materially exceed the equity cushion.

Output two files in `/root/output/`.

First, create `/root/output/due_diligence_report.json` with this schema:

```json
{
  "property": {
    "case_id": "string",
    "parcel_id": "string",
    "address": "string",
    "county": "string",
    "state": "string",
    "owner_or_borrower": "string"
  },
  "sale": {
    "sale_type": "string",
    "selling_authority": "string",
    "auction_date": "YYYY-MM-DD",
    "opening_bid": 0,
    "sale_status": "active | postponed | cancelled | stayed | unclear",
    "status_reason": "string"
  },
  "claims": [
    {
      "claimant": "string",
      "claim_type": "string",
      "source_id": "string",
      "recorded_date": "YYYY-MM-DD or null",
      "amount": 0,
      "priority": "senior | foreclosing | junior | unknown",
      "treatment": "survives_sale | paid_from_sale | extinguished_by_sale | requires_counsel_review",
      "reason": "string"
    }
  ],
  "risk_flags": [
    {
      "risk_type": "string",
      "severity": "low | medium | high | blocker",
      "source_id": "string",
      "summary": "string",
      "recommended_action": "string"
    }
  ],
  "valuation": {
    "as_is_value_low": 0,
    "as_is_value_high": 0,
    "arv_mid": 0,
    "repair_reserve": 0,
    "eviction_reserve": 0,
    "closing_cost_reserve": 0,
    "surviving_debt_total": 0,
    "recommended_max_bid": 0
  },
  "recommendation": {
    "decision": "BID | BID_WITH_CONDITIONS | DO_NOT_BID",
    "primary_reasons": ["string"],
    "conditions_before_bid": ["string"]
  },
  "open_issues": [
    {
      "issue": "string",
      "why_it_matters": "string",
      "next_step": "string"
    }
  ],
  "evidence_index": [
    {
      "source_id": "string",
      "source_location": "string",
      "supports": "string"
    }
  ]
}
```

Second, create `/root/output/due_diligence_memo.md` with these sections:
- Property
- Sale Status
- Lien and Title Summary
- Risk Flags
- Valuation
- Recommendation
- Open Issues

Use numeric values for money fields in JSON, not formatted strings. If a required amount is unavailable, use `null` and explain the issue in `open_issues`. Do not treat missing values as zero.

Do not modify files under `/root/input/`, `/root/tests/`, `/root/environment/`, or `/root/environment/skills/`.

Do not hard-code verifier behavior, create hidden answer files, delete source records, fabricate evidence, or replace the diligence work with a generic legal disclaimer.
