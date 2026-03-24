Complete the workbook at `/root/data/store_reorder_forecast.xlsx`.

The workbook already contains:
- `DailySales`: store-SKU daily unit sales history with inventory fields repeated on each row
- `Forecast14D`: an empty worksheet for 14 future daily forecasts
- `ReorderAlerts`: an empty worksheet for replenishment decisions

Column definitions are summarized in `/root/data/store-sales-readme.md`.

Do not alter `DailySales`. Write plain values to the output sheets; formulas are not required.

Each `StoreID` + `SKU` pair has exactly 35 historical daily rows:
- use the earliest 28 dates as the training window
- use the latest 7 dates as the backtest window

Create `Forecast14D` with one row per future forecast date for every `StoreID` + `SKU` pair.
Sort rows by `StoreID`, then `SKU`, then `ForecastDate` ascending.
Create these columns in this exact order:
1. `StoreID`
2. `SKU`
3. `Category`
4. `ForecastDate`
5. `Weekday`
6. `MovingAverageBaseline`
7. `WeekdayFactor`
8. `ForecastUnits`
9. `BacktestMAE`
10. `BacktestWAPEPct`

Forecast rules for each `StoreID` + `SKU` pair:
- `MovingAverageBaseline`: mean of `UnitsSold` from the last 7 rows of the 28-row training window, rounded to 2 decimals
- `WeekdayFactor`: for each weekday, mean `UnitsSold` on that weekday in the 28-row training window divided by the overall mean `UnitsSold` in the same 28-row training window, rounded to 4 decimals in the final sheet
- Backtest prediction for each of the 7 holdout dates: `MovingAverageBaseline * WeekdayFactor` for that holdout date's weekday
- `BacktestMAE`: mean absolute error across the 7 backtest dates, rounded to 2 decimals
- `BacktestWAPEPct`: `sum(abs(actual - predicted)) / sum(actual) * 100`, rounded to 2 decimals
- Future forecast dates start on the day after the latest date in `DailySales` for that series and continue for 14 consecutive calendar days
- `ForecastUnits = MovingAverageBaseline * WeekdayFactor` for the forecast date's weekday, rounded to 2 decimals
- `Weekday` must be the English weekday name such as `Monday`

Create `ReorderAlerts` with one row per `StoreID` + `SKU` pair.
Sort rows by `RecommendedOrderUnits` descending, then `StoreID`, then `SKU` ascending.
Create these columns in this exact order:
1. `StoreID`
2. `SKU`
3. `Category`
4. `LatestActualDate`
5. `LatestOnHandUnits`
6. `LeadTimeDays`
7. `MinDisplayUnits`
8. `AvgForecastNext14D`
9. `LeadTimeForecastUnits`
10. `ReorderPointUnits`
11. `CoverageDays14D`
12. `RecommendedOrderUnits`
13. `AlertLevel`

Reorder rules for each `StoreID` + `SKU` pair:
- `LatestActualDate`: latest historical date for the series
- `LatestOnHandUnits`, `LeadTimeDays`, and `MinDisplayUnits`: take the values from the historical rows for that series
- `AvgForecastNext14D`: mean of the 14 future `ForecastUnits`, rounded to 2 decimals
- `LeadTimeForecastUnits`: sum of the first `LeadTimeDays` future `ForecastUnits`, rounded to 2 decimals
- `ReorderPointUnits = ceil(LeadTimeForecastUnits + MinDisplayUnits)`
- `CoverageDays14D = LatestOnHandUnits / AvgForecastNext14D`, rounded to 2 decimals
- `RecommendedOrderUnits = max(0, ceil(ReorderPointUnits - LatestOnHandUnits))`
- `AlertLevel`:
  - `Critical` if `LatestOnHandUnits < LeadTimeForecastUnits`
  - `Reorder` if `LatestOnHandUnits >= LeadTimeForecastUnits` and `LatestOnHandUnits < ReorderPointUnits`
  - `OK` otherwise

Save the completed workbook in place at `/root/data/store_reorder_forecast.xlsx`.
