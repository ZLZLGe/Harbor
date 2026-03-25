You are auditing meal reimbursement claims for a distributed team.

Input file in `/root/data/`:
1. `transfer2_claims.json`

Use the bundled city restaurant lookup instead of memory.

Produce this file in `/root/`:
1. `transfer2_claim_audit.json`

Requirements:
1. Search restaurants separately for every claim city.
2. Match the claimed restaurant name exactly after trimming leading and trailing spaces.
3. If the restaurant is not found in the claimed city, mark the claim as rejected with `["not_found"]`.
4. If the restaurant is found, evaluate these checks in order:
   - cuisine list contains `required_cuisine`, case-insensitively
   - `Average Cost` is at most `max_average_cost`
   - `Aggregate Rating` is at least `min_aggregate_rating`
5. Build the `reasons` array in this exact order when applicable:
   - `cuisine_mismatch`
   - `cost_exceeded`
   - `rating_below_min`
6. Claims with an empty `reasons` array are `approved`; otherwise they are `rejected`.
7. Write a JSON object with these top-level keys:
   - `batch_name`
   - `approved_claim_ids`
   - `claim_reviews`
   - `tool_called`
8. `claim_reviews` must preserve the input order.
9. Each claim review must contain:
   - `claim_id`
   - `status`
   - `reasons`
   - `matched_restaurant`
   - `average_cost`
   - `aggregate_rating`
10. For not-found claims, set `matched_restaurant`, `average_cost`, and `aggregate_rating` to `null`.
11. Set `tool_called` to `["search_restaurants"]`.
