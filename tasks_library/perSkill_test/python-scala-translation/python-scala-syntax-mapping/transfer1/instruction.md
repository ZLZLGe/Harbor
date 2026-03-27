# Audit Candidate Scala Rewrites

A migration review file is available at `/root/audit_candidates.csv`.

Create exactly one file:
- `/outputs/syntax_mapping_audit.csv`

Output contract:
1. The output must be a CSV with header:
   `case_id,python,proposed_scala,is_correct,correct_scala`
2. Preserve input row order.
3. `is_correct` must be lowercase `true` or `false`.
4. `correct_scala` must contain the canonical Scala equivalent for each Python snippet.

Success criteria:
- `/outputs/syntax_mapping_audit.csv` exists and contains correct audit judgments and corrections.
