You are cleaning up a small library catalog export after a migration created duplicate bibliographic records.

Input files available in `/root`:
- `catalog_export.csv`
- `circulation_history.csv`

Create `build_merge_candidates.py` and run it. The script must read both CSV files and produce:
- `catalog_merge_candidates.csv`
- `catalog_merge_summary.json`

Do not modify the input files.

`catalog_export.csv` columns:
- `record_id`
- `title`
- `author`
- `isbn`
- `format`
- `publication_year`
- `owning_branch`
- `copy_count`
- `audience`

`circulation_history.csv` columns:
- `loan_id`
- `record_id`
- `checkout_date`
- `return_status`

Use these fixed consolidation rules:
- Sort catalog rows by `record_id` before deriving any grouped results
- `normalized_isbn` is the uppercase ISBN after removing spaces and hyphens; leave it blank when the input ISBN is blank
- `normalized_title` is built by lowercasing `title`, replacing `&` with `and`, removing every remaining character that is not a letter, digit, or space, collapsing repeated spaces, and trimming outer spaces
- `normalized_author` is built from `author` using the same normalization rule as `normalized_title`
- `loan_count_2025` is the number of circulation rows for that `record_id` whose `checkout_date` is in calendar year 2025
- An ISBN-based duplicate candidate is a maximal group of at least 2 catalog rows with the same non-blank `normalized_isbn` and the same `format`
- A title-based duplicate candidate is a maximal group of at least 2 catalog rows where `normalized_isbn` is blank for every row in the group and all rows share the same `normalized_title`, `normalized_author`, `format`, `publication_year`, and `audience`
- `preferred_record_id` is the record in the candidate group with the highest `loan_count_2025`; break ties by higher `copy_count`, then by smaller `record_id`
- `merge_record_ids` is the semicolon-delimited list of all non-preferred `record_id` values in ascending order
- `all_record_ids` is the semicolon-delimited list of every `record_id` in the candidate group in ascending order
- `branches_covered` is the number of distinct `owning_branch` values in the candidate group
- `total_copy_count` is the sum of `copy_count` in the candidate group
- `recent_loan_count` is the sum of `loan_count_2025` in the candidate group
- `title_variant_count` is the number of distinct original `title` strings in the candidate group after trimming outer spaces only
- `confidence_reason` must be `same_normalized_isbn_and_format` for ISBN-based candidates and `same_normalized_title_author_year_audience_format` for title-based candidates

Write `catalog_merge_candidates.csv` with exactly these columns in this exact order:
1. `candidate_id`
2. `match_basis`
3. `normalized_isbn`
4. `normalized_title`
5. `normalized_author`
6. `format`
7. `preferred_record_id`
8. `merge_record_ids`
9. `all_record_ids`
10. `member_count`
11. `branches_covered`
12. `total_copy_count`
13. `recent_loan_count`
14. `title_variant_count`
15. `confidence_reason`

Output requirements:
- Export one row per duplicate candidate group
- Sort rows with all `isbn` candidates first, then all `title_author` candidates; within each basis, sort by `normalized_title`, then `preferred_record_id`
- After the final sort, assign `candidate_id` values as `MERGE-001`, `MERGE-002`, and so on
- `match_basis` must be lowercase `isbn` or `title_author`
- Keep blank string fields empty rather than writing placeholder text
- Keep count fields as integers

Write `catalog_merge_summary.json` with exactly these top-level keys:
- `candidate_count`
- `isbn_based_candidates`
- `title_based_candidates`
- `records_flagged_for_merge`
- `preferred_records_with_zero_2025_loans`
- `max_candidate_size`
- `total_recent_loan_count`

Summary requirements:
- `preferred_records_with_zero_2025_loans` must be sorted ascending
- Keep numeric summary values as integers
