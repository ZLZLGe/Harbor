Review the covenant package document in `/root/` together with `/root/quarterly_financials.xlsx`.

The package document defines the covenant formulas, date-based threshold schedule, metric order, and the waiver / carve-out rules that change how each test date should be evaluated. Use the worksheet named `Quarterly Results`. Only rows where `Testing Eligible = Yes` are testing dates; use the current row's balance sheet values and trailing four-quarter sums for flow items.

Write `/root/covenant_breach_summary.json` as UTF-8 JSON with exactly this shape:

```json
{
  "breach_periods": [
    {
      "test_period": "YYYY-MM-DD",
      "breaches": [
        {
          "metric": "Metric name from the covenant package document",
          "actual": 0.000,
          "threshold": 0.000,
          "breach_direction": "above_maximum",
          "deviation": 0.000
        }
      ]
    }
  ],
  "most_severe_breach": {
    "test_period": "YYYY-MM-DD",
    "metric": "Metric name from the covenant package document",
    "actual": 0.000,
    "threshold": 0.000,
    "breach_direction": "above_maximum",
    "deviation": 0.000
  }
}
```

Additional requirements:

- Round `actual`, `threshold`, and `deviation` to 3 decimal places.
- Sort `breach_periods` chronologically.
- Inside each test period, keep breached metrics in the same order shown in the covenant package document.
- `most_severe_breach` must be the single largest post-waiver deviation across all tested dates.
- Do not write any extra keys or commentary.
