# Store Sales Workbook Notes

## DailySales

- `Date`: ISO 8601 calendar date for the store-SKU observation
- `StoreID`: store identifier
- `SKU`: item identifier
- `Category`: merchandise category
- `UnitsSold`: realized unit sales for that day
- `OnHandUnits`: current on-hand inventory snapshot for the series
- `LeadTimeDays`: replenishment lead time in whole days
- `MinDisplayUnits`: minimum units that should remain available on shelf

Each `StoreID` + `SKU` pair contains 35 daily observations without gaps.
