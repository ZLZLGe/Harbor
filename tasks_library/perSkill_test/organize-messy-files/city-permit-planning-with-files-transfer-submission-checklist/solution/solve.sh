#!/bin/bash
set -euo pipefail

TASK_ROOT="${TASK_ROOT:-/root}"
PERMIT_ROOT="${PERMIT_ROOT:-${TASK_ROOT}/permit_workspace}"
DELIVERABLE_DIR="${TASK_ROOT}/deliverables"
OUTPUT_PATH="${DELIVERABLE_DIR}/permit_submission_checklist.csv"

mkdir -p "${DELIVERABLE_DIR}"

cat > "${TASK_ROOT}/task_plan.md" <<'EOF'
# Task Plan

1. Review the rule excerpt and intake email to identify the required checklist items and blocker criteria.
2. Cross-check the permit application, authorization letter, drawings, and quotes for the eight required item IDs.
3. Record satisfied, missing, and conflicting items in ${OUTPUT_PATH} with evidence paths and blocker flags.

Checklist focus:
- accessibility_ramp_details
- neighbor_notification_affidavit
- owner_authorization
- parcel_identifier_consistency
- permit_application_signature
- project_valuation_support
- stormwater_worksheet
- utility_service_alignment
EOF

cat > "${TASK_ROOT}/findings.md" <<'EOF'
# Findings

- `permit_application.csv` shows `applicant_signed=yes`, parcel `417-19-008`, valuation `185000`, and requested electrical service `400A`.
- `owner_authorization.txt` is signed by Riverview Holdings LLC and authorizes Northbank Hospitality LLC to submit.
- `site_plan.svg` includes ramp details (`1:12` slope and `60x60 in` landing) but shows APN `417-19-006`, which conflicts with the application.
- `electrical_riser.svg` specifies a new `320A` panel, which conflicts with the `400A` request in the application.
- The email says a stormwater worksheet and neighbor notification affidavit are required and were not found in the package.
- `project_cost_breakdown.csv`, `general_contractor_quote.txt`, and `traffic_control_quote.txt` support the declared valuation total of `185000`.
EOF

cat > "${TASK_ROOT}/progress.md" <<EOF
# Progress

Completed the permit package review, captured the conflicting APN and utility values, noted the two missing required submittals, and wrote ${OUTPUT_PATH}.
EOF

cat > "${OUTPUT_PATH}" <<'EOF'
item_id,requirement,status,evidence,blocking_issue,notes
accessibility_ramp_details,Site plan must show accessibility ramp dimensions and slope,satisfied,permit_workspace/drawings/site_plan.svg; permit_workspace/drawings/accessibility_ramp_schedule.csv,no,"Ramp details are present with a 1:12 slope, 60x60 in landing, and handrails on both sides."
neighbor_notification_affidavit,Neighbor notification affidavit is required for alley-facing work,missing,permit_workspace/rules/city_checklist_excerpt.md; permit_workspace/emails/plan_review_followup.md,yes,"Rules and the reviewer email require the affidavit because the project fronts the alley, but no affidavit file is present."
owner_authorization,Owner authorization letter is required when the applicant is not the owner,satisfied,permit_workspace/forms/permit_application.csv; permit_workspace/forms/owner_authorization.txt,no,"The application lists Northbank Hospitality LLC as applicant and Riverview Holdings LLC as owner, and the signed authorization letter is included."
parcel_identifier_consistency,Parcel identifier must match across the application and drawings,conflict,permit_workspace/forms/permit_application.csv; permit_workspace/drawings/site_plan.svg; permit_workspace/emails/plan_review_followup.md,yes,"The application shows parcel 417-19-008 while the site plan shows APN 417-19-006, so the package has a blocker-level APN conflict."
permit_application_signature,Permit application must be signed,satisfied,permit_workspace/forms/permit_application.csv,no,"The permit application explicitly shows applicant_signed=yes."
project_valuation_support,Declared valuation must be supported by attached quotes,satisfied,permit_workspace/forms/permit_application.csv; permit_workspace/forms/project_cost_breakdown.csv; permit_workspace/quotes/general_contractor_quote.txt; permit_workspace/quotes/traffic_control_quote.txt,no,"The 172400 general construction quote plus the 12600 traffic-control quote total 185000, matching the application valuation."
stormwater_worksheet,Stormwater worksheet is required when impervious area exceeds 800 square feet,missing,permit_workspace/forms/permit_application.csv; permit_workspace/rules/city_checklist_excerpt.md; permit_workspace/emails/plan_review_followup.md,yes,"The application and site plan show 960 sq ft of new impervious area, and the reviewer noted that the stormwater worksheet was not included."
utility_service_alignment,Requested electrical service must match between forms and drawings,conflict,permit_workspace/forms/permit_application.csv; permit_workspace/drawings/electrical_riser.svg; permit_workspace/emails/plan_review_followup.md,yes,"The permit application requests 400A but the electrical riser calls for a 320A panel, so the utility figures are inconsistent."
EOF
