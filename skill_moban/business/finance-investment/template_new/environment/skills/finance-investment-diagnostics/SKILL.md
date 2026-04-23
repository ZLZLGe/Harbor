---
name: finance-investment-diagnostics
description: Use for SEC Company Facts extraction, public-equity financial statement analysis, market-risk calculations, DCF valuation, and investment ranking tasks.
---

# Finance Investment Diagnostics

Use this skill when a task asks for public-equity analysis from SEC Company Facts, daily adjusted prices, FRED rates, DCF valuation, or investment recommendations.

## Fast Workflow

1. Read `/app/data/reference/company_universe.csv` and `/app/data/reference/methodology.md` first.
2. Use SEC Company Facts JSON directly; do not refetch data.
3. Build one financial table with the latest three complete fiscal years per ticker.
4. Compute one score row per ticker from latest fiscal-year quality metrics and 252-trading-day price risk.
5. Compute valuation and recommendation after the score components are available.
6. Write all final artifacts to `/app/output` and cross-check that memo, CSV, and JSON agree.

For this template shape, the fastest safe path is to run the bundled scaffold and then inspect the produced files:

```bash
python /app/.codex/skills/finance-investment-diagnostics/tools/build_outputs.py
```

The scaffold only uses `/app/data` and the formulas in `methodology.md`; it writes the five required artifacts to `/app/output`. If you modify the scaffold, keep the same SEC fact selection order, ranking tie-breaks, and memo/JSON consistency checks.

## SEC Concept Map

Use these concept families, in order:

- Revenue: `RevenueFromContractWithCustomerExcludingAssessedTax`, `Revenues`, `SalesRevenueNet`, `SalesRevenueGoodsNet`
- Operating income: `OperatingIncomeLoss`
- Net income: `NetIncomeLoss`
- Operating cash flow: `NetCashProvidedByUsedInOperatingActivities`
- Capital expenditures: `PaymentsToAcquirePropertyPlantAndEquipment`, `PaymentsToAcquireProductiveAssets`
- Cash: `CashAndCashEquivalentsAtCarryingValue`, `CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents`, `CashAndCashEquivalentsAndShortTermInvestments`
- Current debt: `LongTermDebtAndFinanceLeaseObligationsCurrent`, `LongTermDebtCurrent`, `ShortTermBorrowings`
- Noncurrent debt: `LongTermDebtAndFinanceLeaseObligationsNoncurrent`, `LongTermDebtNoncurrent`
- Total debt fallback: `LongTermDebtAndFinanceLeaseObligations`, `LongTermDebt`
- Equity: `StockholdersEquity`, `StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest`
- Diluted shares: `WeightedAverageNumberOfDilutedSharesOutstanding`, `WeightedAverageNumberOfSharesOutstandingBasic`, `CommonStockSharesOutstanding`
- Diluted EPS: `EarningsPerShareDiluted`

Filter annual facts to `form == "10-K"` and `fp == "FY"`. If several records remain for the same fiscal year, take the latest `filed` date.

## Calculation Reminders

- Capital expenditures should be reported as a positive cash outflow.
- Free cash flow is operating cash flow minus capital expenditures.
- Use adjusted close prices and the latest common price date across all tickers and SPY.
- Use 253 adjusted-close observations to compute 252 daily returns.
- Annualized volatility is sample standard deviation of daily returns times `sqrt(252)`.
- Beta is covariance of aligned asset and SPY returns divided by SPY return variance.
- Sharpe uses annual DGS10 divided by 100, then daily risk-free rate as `risk_free_rate / 252`.
- Rank by composite score descending; break ties by base upside descending, then ticker ascending.

## Useful Probe

Run the probe to inspect available SEC concept coverage before coding the final package:

```bash
python /app/.codex/skills/finance-investment-diagnostics/tools/probe_sec_facts.py
```

The probe prints each ticker's latest complete fiscal years and which concepts were found.
