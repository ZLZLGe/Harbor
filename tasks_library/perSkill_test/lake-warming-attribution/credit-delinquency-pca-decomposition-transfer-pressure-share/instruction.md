The folder `/root/data/` contains one monthly consumer-credit portfolio slice per row, keyed by `portfolio_id`, across four files:

- `borrower_profile.csv`
- `payment_behavior.csv`
- `regional_cost_panel.csv`
- `delinquency_targets.csv`

The response variable is `delinquency_rate_pct` from `delinquency_targets.csv`. The 12 driver variables belong to four pressure categories:

- Debt Load: `debt_to_income_ratio`, `credit_utilization_pct`, `installment_balance_growth_pct`
- Income Volatility: `income_variability_pct`, `hours_worked_cv_pct`, `recent_job_change_pct`
- Repayment Friction: `minimum_payment_share_pct`, `days_since_autopay_fail`, `roll_rate_30_to_59_pct`
- Cost Pressure: `rent_to_income_pct`, `utility_cost_index`, `essentials_inflation_pct`

Merge the four files on `portfolio_id`, use all 12 driver variables together in one global dimensionality-reduction step, keep 4 factors, and apply an orthogonal rotation so the factors are interpretable.

Assign each rotated factor to the category whose variables have the largest mean absolute loading on that factor.

Then regress `delinquency_rate_pct` on the rotated factor scores. For each category, create a leave-out prediction by setting the coefficient of every factor assigned to that category to zero while keeping the intercept and all other factor coefficients unchanged. Define that category's raw contribution as the increase in mean squared prediction error relative to the full factor model. If a category receives no factors, its raw contribution is 0.

Normalize the four raw contributions so their shares sum to 100.

Write `/root/output/delinquency_pressure_share.csv` with exactly these columns:

- `category`
- `share_pct`

Only include the single dominant category as one row, with `share_pct` reported as a percentage.
