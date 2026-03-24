You are working in `/root`.

A municipal permit submission package is available at `/root/permit_workspace`. It includes intake forms, plan-review email notes, drawing extracts, quotes, and a rule excerpt for a small commercial exterior alteration.

Your job:

1. Review the evidence in `/root/permit_workspace`.
2. Assess these eight checklist items:
   - `accessibility_ramp_details`
   - `neighbor_notification_affidavit`
   - `owner_authorization`
   - `parcel_identifier_consistency`
   - `permit_application_signature`
   - `project_valuation_support`
   - `stormwater_worksheet`
   - `utility_service_alignment`
3. Write `/root/deliverables/permit_submission_checklist.csv`.
4. Keep three working notes in `/root` while you work:
   - `task_plan.md`
   - `findings.md`
   - `progress.md`

Requirements for `/root/deliverables/permit_submission_checklist.csv`:

- Use exactly these columns in this exact order:
  - `item_id`
  - `requirement`
  - `status`
  - `evidence`
  - `blocking_issue`
  - `notes`
- Include exactly 8 data rows, one for each required checklist item listed above.
- Sort the rows alphabetically by `item_id`.
- `status` must be one of:
  - `satisfied`
  - `missing`
  - `conflict`
- `evidence` must cite one or more specific files from `/root/permit_workspace`.
- `blocking_issue` must be either `yes` or `no`.
- `notes` must briefly explain why the item is satisfied, missing, or conflicting.

Interpretation rules:

- Use `satisfied` when the package contains enough consistent evidence for that item.
- Use `missing` when a required document or worksheet is not present in the package.
- Use `conflict` when the package contains contradictory values that would stop intake review.

Do not modify the evidence files. The goal is to analyze the package and produce the CSV checklist plus the three working notes.
