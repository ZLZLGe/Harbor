# Methodology

This task uses frozen public data snapshots. Do not fetch fresh data while solving.

## Fiscal-Year Fact Selection

For each ticker, use the SEC Company Facts file in `/app/data/sec_companyfacts/<ticker>.json`.

For each concept and fiscal year, prefer facts in this order:
1. `form == "10-K"`
2. `fp == "FY"`
3. latest `filed` date
4. units matching the requested measure

Use the latest three fiscal years that have the core income statement, cash-flow, balance-sheet, share-count, and EPS facts needed by the task.

## Concept Families

Use the first available matching concept in each family:

- Revenue: `RevenueFromContractWithCustomerExcludingAssessedTax`, `Revenues`, `SalesRevenueNet`, `SalesRevenueGoodsNet`
- Operating income: `OperatingIncomeLoss`
- Net income: `NetIncomeLoss`
- Operating cash flow: `NetCashProvidedByUsedInOperatingActivities`
- Capital expenditures: `PaymentsToAcquirePropertyPlantAndEquipment`, `PaymentsToAcquireProductiveAssets`
- Cash: `CashAndCashEquivalentsAtCarryingValue`, `CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents`, `CashAndCashEquivalentsAndShortTermInvestments`
- Current debt: `LongTermDebtAndFinanceLeaseObligationsCurrent`, `LongTermDebtCurrent`, `ShortTermBorrowings`
- Noncurrent debt: `LongTermDebtAndFinanceLeaseObligationsNoncurrent`, `LongTermDebtNoncurrent`
- Total debt fallback: `LongTermDebtAndFinanceLeaseObligations`, `LongTermDebt`
- Stockholders equity: `StockholdersEquity`, `StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest`
- Diluted shares: `WeightedAverageNumberOfDilutedSharesOutstanding`, `WeightedAverageNumberOfSharesOutstandingBasic`, `CommonStockSharesOutstanding`
- Diluted EPS: `EarningsPerShareDiluted`

Report capital expenditures as a positive cash outflow. Free cash flow equals operating cash flow minus capital expenditures.

## Quality Metrics

- `revenue_cagr_3y = (latest_revenue / earliest_revenue) ** (1 / year_gap) - 1`
- `operating_margin_latest = latest_operating_income / latest_revenue`
- `net_margin_latest = latest_net_income / latest_revenue`
- `fcf_margin_latest = latest_free_cash_flow / latest_revenue`
- `return_on_equity_latest = latest_net_income / latest_stockholders_equity`
- `net_cash_to_revenue_latest = (latest_cash_and_equivalents - latest_total_debt) / latest_revenue`
- `eps_growth_3y = (latest_diluted_eps / earliest_diluted_eps) ** (1 / year_gap) - 1`

If the fiscal-year gap is larger than 2 because a company has a missing year, still use the actual year gap in the CAGR exponent.

## Market Risk Metrics

Use adjusted close prices from `/app/data/prices/<ticker>.csv` and `/app/data/prices/SPY.csv`.

Use the latest common price date across all analyzed tickers and SPY as `as_of_date`. For each ticker, use the last 253 available adjusted close observations up to `as_of_date`, producing 252 daily returns.

- `total_return_252d = last_adj_close / first_adj_close - 1`
- `annualized_volatility = sample_std(daily_returns) * sqrt(252)`
- `max_drawdown = min(price / cumulative_max(price) - 1)`
- `beta_to_spy = covariance(asset_returns, spy_returns) / variance(spy_returns)`, aligned by date
- `sharpe_ratio = mean(daily_returns - risk_free_rate / 252) * 252 / annualized_volatility`

Use the latest numeric DGS10 observation on or before `as_of_date`, divided by 100, as the annual risk-free rate.

## DCF Valuation

Use a five-year free-cash-flow projection plus terminal value.

Constants:
- `equity_risk_premium = 0.05`
- `base_terminal_growth = 0.025`
- `bull_terminal_growth = 0.035`
- `bear_terminal_growth = 0.015`

Discount rate:
- `discount_rate = risk_free_rate + beta_to_spy * equity_risk_premium`
- clamp discount rate to `[0.07, 0.14]`

Growth assumptions:
- `base_growth = clamp(revenue_cagr_3y, 0.02, 0.18)`
- `bull_growth = min(base_growth + 0.03, 0.22)`
- `bear_growth = max(base_growth - 0.04, 0.00)`

For each scenario:
- Project free cash flow for years 1-5 using the scenario growth rate.
- Terminal value equals `year_5_fcf * (1 + terminal_growth) / (discount_rate - terminal_growth)`.
- Equity value equals present value of projected FCF plus present value of terminal value plus cash minus debt.
- Per-share fair value equals equity value divided by diluted shares.

Then:
- `base_upside_pct = base_fair_value / latest_price - 1`
- `margin_of_safety = (base_fair_value - latest_price) / base_fair_value`

## Composite Score And Recommendation

Compute z-scores across the seven-company universe. If a metric has zero standard deviation, its z-score contribution is 0.

- quality component: average z-score of revenue CAGR, operating margin, FCF margin, return on equity, net cash to revenue, and EPS growth
- risk component: average z-score of total return, Sharpe ratio, max drawdown, and negative annualized volatility
- value component: average z-score of base upside percentage, margin of safety, and free-cash-flow yield
- `composite_score = 0.40 * quality_component + 0.25 * risk_component + 0.35 * value_component`

Rank companies by composite score descending. Break ties by base upside percentage descending, then ticker ascending.

Recommendation:
- `buy` if base upside is at least 15% and composite score is positive
- `avoid` if base upside is below -25% or composite score is in the bottom two ranks and max drawdown is worse than -35%
- `trim` if base upside is below -5% or max drawdown is worse than -45%
- otherwise `hold`
