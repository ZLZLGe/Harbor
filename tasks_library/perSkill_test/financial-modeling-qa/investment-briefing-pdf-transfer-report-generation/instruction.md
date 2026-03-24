Create the required four-page briefing document from these input files:

- `/root/portfolio_holdings.csv`
- `/root/performance_attribution.csv`
- `/root/risk_notes.json`

Write the briefing to the task's required output location.

The document must have four pages in this order:

1. A title page containing all of these lines:
   - `Investment Committee Briefing`
   - `North Harbor Multi-Asset Portfolio`
   - `Report Period: Q1 2026`
   - `Committee Meeting Date: 2026-04-15`
2. An `Executive Summary` page containing one narrative paragraph. That paragraph must explicitly include all of these facts and phrasings:
   - `ahead of the 60/20/10/10 Policy Blend by 63 bps`
   - `The top holding was NVDA at 9.4% of capital`
   - `the top five holdings represented 37.2% of the portfolio`
   - `Public Equities was the strongest attribution sleeve at 412 bps`
   - `Real Assets was the weakest at -10 bps`
   - `net exposure at 96%, gross exposure at 118%, tracking error at 4.2%, and five-day liquidity at 87%`
3. A `Performance Attribution` page with a table that reproduces every row from `performance_attribution.csv` in the same order.
4. A `Risk Watchlist` page that lists every risk item from `risk_notes.json`, including severity, owner, and mitigation, and also includes the escalation note.

Do not create any extra output files. Only write the required briefing document.
