Analyze `/root/draft_board_workbook.xlsx` and write `/root/draft_board.csv`.

Use these sheets:

- `Prospect Pool`
- `Athletic Testing`
- `Game Splits`
- `Position Coefficients`
- `Availability Discounts`
- `Board Rules`

The workbook also contains an old board tab that is not part of the current class.

Only include prospects from `Prospect Pool` where:

- `Eligible` is `Y`
- `Scouted Minutes` is at least the `Min Minutes` value from `Board Rules`

For each included prospect:

1. Look up the matching row in `Athletic Testing` by `Prospect ID`.
2. Compute `athletic_score = 0.40 * Burst Score + 0.35 * Movement Score + 0.25 * Strength Score`.
3. Look up the matching row in `Game Splits` by `Prospect ID`.
4. Compute `split_score = 0.20 * Early Grade + 0.50 * Conference Grade + 0.30 * Postseason Grade + Shot Creation Bonus`.
5. Look up the matching row in `Position Coefficients` by `Position`.
6. Look up the matching row in `Availability Discounts` by `Injury Band`.
7. Compute `base_score = athletic_score * Athletic Weight + split_score * Split Weight + Positional Bonus + Interview Bonus`.
8. Compute `composite_score = ROUND(base_score * Multiplier - Availability Penalty, 2)`.

Sort all included prospects by:

1. `composite_score` descending
2. `Conference Grade` descending
3. `Prospect ID` ascending

Keep only the first `Shortlist Size` rows from `Board Rules`.

Write CSV with exactly this header:

`rank,prospect_id,name,position,school,injury_band,composite_score`

`rank` starts at 1. Format `composite_score` with exactly two decimal places. Do not write any extra files.
