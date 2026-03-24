Complete the workbook at `/root/data/campaign_lift_analysis.xlsx`.

The workbook already contains:
- `ExposureSummary`: store-level visitor and purchaser counts for each experiment group
- `Orders`: one row per completed order with realized revenue
- `Analysis`: an empty worksheet for your output

Column notes are summarized in `/root/data/campaign-readme.md`.

Populate `Analysis` with one row per `CampaignGroup`, using this exact row order:
1. `Control`
2. `Bundle`
3. `Discount`
4. `Loyalty`

Write plain values to `Analysis`; formulas are not required.

Create these columns in this exact order:
1. `CampaignGroup`
2. `StoreCount`
3. `TotalVisitors`
4. `TotalPurchasers`
5. `TotalRevenue`
6. `ConversionRate`
7. `ConversionRateSE`
8. `AverageOrderRevenue`
9. `AverageOrderRevenueSE`
10. `AbsLiftVsControl_ConversionRate`
11. `RelLiftVsControl_ConversionRatePct`
12. `ConversionRateLiftSE`
13. `ConversionRateLiftCI95Low`
14. `ConversionRateLiftCI95High`
15. `AbsLiftVsControl_AOV`
16. `RelLiftVsControl_AOVPct`
17. `AOVLiftSE`
18. `AOVLiftCI95Low`
19. `AOVLiftCI95High`
20. `Decision`

Metric rules:
- `StoreCount`: distinct `StoreID` count from `ExposureSummary`
- `TotalVisitors`: sum of `Visitors`
- `TotalPurchasers`: sum of `Purchasers`
- `TotalRevenue`: sum of `Revenue` from `Orders`
- `ConversionRate = TotalPurchasers / TotalVisitors`
- `ConversionRateSE = sqrt(ConversionRate * (1 - ConversionRate) / TotalVisitors)`
- `AverageOrderRevenue = TotalRevenue / TotalPurchasers`
- `AverageOrderRevenueSE = sample standard deviation of order-level Revenue within the group, divided by sqrt(TotalPurchasers), using ddof=1`

Lift rules, always versus the `Control` row:
- `AbsLiftVsControl_ConversionRate = group ConversionRate - control ConversionRate`
- `RelLiftVsControl_ConversionRatePct = (group ConversionRate / control ConversionRate - 1) * 100`
- `ConversionRateLiftSE = sqrt(group ConversionRateSE^2 + control ConversionRateSE^2)`
- `ConversionRateLiftCI95Low = AbsLiftVsControl_ConversionRate - 1.96 * ConversionRateLiftSE`
- `ConversionRateLiftCI95High = AbsLiftVsControl_ConversionRate + 1.96 * ConversionRateLiftSE`
- `AbsLiftVsControl_AOV = group AverageOrderRevenue - control AverageOrderRevenue`
- `RelLiftVsControl_AOVPct = (group AverageOrderRevenue / control AverageOrderRevenue - 1) * 100`
- `AOVLiftSE = sqrt(group AverageOrderRevenueSE^2 + control AverageOrderRevenueSE^2)`
- `AOVLiftCI95Low = AbsLiftVsControl_AOV - 1.96 * AOVLiftSE`
- `AOVLiftCI95High = AbsLiftVsControl_AOV + 1.96 * AOVLiftSE`

Control row rules:
- Both absolute lift columns must be `0`
- Both relative lift columns must be `0`
- Both lift SE columns must still be computed against the control row, so they are not zero
- `Decision` must be `Control`

Decision rules for non-control rows:
- `Significant Winner` if both `ConversionRateLiftCI95Low > 0` and `AOVLiftCI95Low > 0`
- Otherwise `No Clear Win`

Rounding rules:
- Round `TotalRevenue` to 2 decimals
- Round conversion-rate-related numeric columns to 6 decimals
- Round AOV-related numeric columns to 4 decimals
- Round relative lift percentage columns to 2 decimals

Do not alter `ExposureSummary` or `Orders`. Save the completed workbook in place at `/root/data/campaign_lift_analysis.xlsx`.
