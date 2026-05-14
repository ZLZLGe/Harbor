You need to prepare a seed fundraising package for NoticeFlow, a rental notice and landlord-tenant workflow SaaS serving property managers and housing-focused law firms in three U.S. metros.

Input data is under `/root/data/`:

- `round_brief.json`: round terms, approved metro scope, current cash, and model start quarter.
- `market_snapshots/metro_housing_snapshot.csv`: metro-level market snapshot for Atlanta, Dallas, and Phoenix.
- `company_notes/pricing_and_traction.yaml`: current pricing and operating metrics.
- `company_notes/base_case_assumptions.csv`: quarterly planning assumptions for multiple planning scenarios.
- `company_notes/milestones.csv`: approved milestone plan.
- `company_notes/positioning.md`: product and customer context.
- `draft_materials/`: older materials and older metric extracts that may conflict with the current inputs.
- `delivery_policy.yaml`: delivery rules, required sections, and modeling rules.

## Your Task

1. Use the current inputs to assemble a complete fundraising fact set for the approved round.
2. Produce an investor memo, a one-pager, an 8-quarter base-case financial model, a use-of-funds table, and a reconciliation log for stale conflicts and material input tensions.
3. Keep the round terms, pricing, traction metrics, market metrics, and milestone timing aligned across all deliverables.
4. Write the structured fact set to a machine-readable file.

## Business Constraints

1. `draft_materials/` is reference material only. If a draft conflicts with the current inputs, use the current inputs.
2. The market scope must include all three metros from `round_brief.json`.
3. `investor_memo.md` and `one_pager.md` must use the same round terms, pricing, traction metrics, and metro data as `fundraising_facts.json`.
4. The financial model must cover exactly 8 sequential quarters, starting from the model start quarter in `round_brief.json`.
5. `company_notes/base_case_assumptions.csv` contains more than one scenario. Use the `base` scenario.
6. `use_of_funds.csv` must sum exactly to the target raise amount.
7. Do not add unsupported customer counts, pricing, market metrics, or milestone dates.
8. Every conflicting value from `draft_materials/` that changes a round term, pricing term, traction metric, or approved market scope must appear in the reconciliation log.
9. If the current approved milestone plan and the approved base-case model create a material tension, record it in the reconciliation log and mention it in the investor memo risk section.

## Output

If `/root/output/` does not exist, create it first.

Write `/root/output/fundraising_facts.json` as a JSON object with this structure:

```json
{
  "company_name": "NoticeFlow",
  "round": {
    "instrument": "",
    "target_raise_usd": 0,
    "minimum_raise_usd": 0,
    "close_target_quarter": "YYYY-Q#",
    "runway_months_target": 0
  },
  "pricing": {
    "property_manager": {
      "monthly_subscription_usd": 0,
      "implementation_fee_usd": 0
    },
    "law_firm": {
      "monthly_subscription_usd": 0,
      "implementation_fee_usd": 0
    }
  },
  "traction": {
    "active_property_manager_customers": 0,
    "active_law_firm_customers": 0,
    "annualized_platform_revenue_usd": 0,
    "pilot_conversion_rate": 0.0,
    "gross_revenue_retention": 0.0
  },
  "markets": [
    {
      "metro": "",
      "renter_households": 0,
      "renter_share_pct": 0.0,
      "median_rent_burden_pct": 0.0,
      "median_gross_rent_usd": 0,
      "median_household_income_usd": 0
    }
  ],
  "milestones": [
    {
      "quarter": "YYYY-Q#",
      "milestone": "",
      "owner": ""
    }
  ]
}
```

Requirements:

- `markets` must contain exactly 3 objects, in the same metro order used by `round_brief.json`.
- `pilot_conversion_rate`, `gross_revenue_retention`, `renter_share_pct`, and `median_rent_burden_pct` must use decimal values between `0` and `1`.
- All money values must be JSON numbers, not strings.
- `milestones` must be ordered by quarter.

Write `/root/output/financial_model.csv` with exactly these columns:

```csv
quarter,beginning_cash_usd,new_property_manager_customers,new_law_firm_customers,ending_property_manager_customers,ending_law_firm_customers,subscription_revenue_usd,implementation_revenue_usd,total_revenue_usd,people_cost_usd,go_to_market_cost_usd,other_opex_usd,net_burn_usd,ending_cash_usd
```

Requirements:

- Include exactly 8 data rows, one per quarter.
- Quarters must be sequential and must start from the model start quarter in `round_brief.json`.
- `total_revenue_usd` must equal `subscription_revenue_usd + implementation_revenue_usd`.
- `net_burn_usd` must equal `people_cost_usd + go_to_market_cost_usd + other_opex_usd - total_revenue_usd`.
- `ending_cash_usd` must equal `beginning_cash_usd - net_burn_usd`.
- Customer counts must roll forward quarter by quarter.

Write `/root/output/use_of_funds.csv` with exactly these columns:

```csv
category,amount_usd,share_of_raise,notes
```

Requirements:

- `share_of_raise` must be a decimal between `0` and `1`.
- The sum of `amount_usd` must equal `round.target_raise_usd` from `fundraising_facts.json`.
- The sum of `share_of_raise` must equal `1.0` within normal floating-point tolerance.

Write `/root/output/reconciliation_log.csv` with exactly these columns:

```csv
field_id,current_value,conflicting_value,conflict_source,resolution_reason
```

Requirements:

- Include every draft-material conflict that changes a round term, pricing term, traction metric, or approved market scope.
- Include any material tension between the approved current inputs and the approved base-case model.
- `field_id` must use only these machine-readable values when applicable: `target_raise_usd`, `minimum_raise_usd`, `instrument`, `property_manager_monthly_subscription_usd`, `law_firm_monthly_subscription_usd`, `annualized_platform_revenue_usd`, `pilot_conversion_rate`, `gross_revenue_retention`, `third_metro`, `active_property_manager_customers`, `active_law_firm_customers`, `pm_customer_milestone_2027_q4`.
- `conflict_source` must use a relative path such as `draft_materials/legacy_metrics.csv`, `draft_materials/investor_memo_old.md`, `draft_materials/one_pager_old.md`, or `current_inputs`.
- `resolution_reason` must use only these machine-readable values: `current_round_brief`, `current_pricing`, `current_traction`, `current_metro_scope`, `risk_callout_required`.

Write `/root/output/investor_memo.md`.

Requirements:

- Start with `# NoticeFlow Investor Memo`.
- Include these section headings exactly once:
  - `## Company`
  - `## Problem`
  - `## Product`
  - `## Market`
  - `## Business Model`
  - `## Traction`
  - `## Raise`
  - `## Use of Funds`
  - `## Risks`
  - `## Milestones`
- Mention Atlanta, Dallas, and Phoenix.
- Include the target raise amount, the instrument, both pricing tiers, and the annualized platform revenue.
- Mention the key milestone-versus-model risk if one exists in the approved inputs.

Write `/root/output/one_pager.md`.

Requirements:

- Start with `# NoticeFlow`.
- Include these section headings exactly once:
  - `## What We Do`
  - `## Why Now`
  - `## Market Snapshot`
  - `## Traction`
  - `## Raise Summary`
- Mention Atlanta, Dallas, and Phoenix.
- Include the target raise amount, the instrument, and the annualized platform revenue.

## Notes

- Do not modify files under `/root/data/`.
- Do not bypass the requested work with cached outputs, placeholders, or unsupported numbers.
- Do not modify verifier files, task metadata, or environment files.
- You may write helper scripts in the working directory, but the required deliverables are the 6 files under `/root/output/`.
