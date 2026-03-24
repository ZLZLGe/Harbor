Review these files:
- `/root/customer_signups.tsv`: new retail customer signup submissions.
- `/root/sanctions_watchlist.json`: sanctioned entities with canonical names, aliases, date of birth, country associations, and sanctions program.

Write `/root/watchlist_hits.tsv` containing only the signups that should be escalated for sanctions review.

Matching guidance:
1. Compare each `submitted_name` against both `primary_name` and all listed aliases, allowing for transliteration drift, token reordering, dropped punctuation, and small spelling errors.
2. Escalate a signup only when exactly one watchlist entity is the clear best name match.
3. A clear name match must also have at least one corroborating attribute:
   - the signup `date_of_birth` exactly equals the watchlist `date_of_birth`, or
   - the signup `country_code` appears in the entity's `risk_countries`.
4. Do not include weak name-only similarities.
5. Do not include ambiguous cases where multiple watchlist entities are comparably plausible.

Output requirements:
- Write a tab-separated file with this exact header order:
  `signup_id	submitted_name	date_of_birth	country_code	matched_entity_id	matched_name	match_basis	program`
- `matched_name` must contain the matched entity's `primary_name`.
- `match_basis` must be one of `DOB`, `Country`, or `DOB+Country`.
- Preserve the original signup values for `submitted_name`, `date_of_birth`, and `country_code`.
- Sort output rows by `signup_id` ascending.
- Do not include clean signups.
