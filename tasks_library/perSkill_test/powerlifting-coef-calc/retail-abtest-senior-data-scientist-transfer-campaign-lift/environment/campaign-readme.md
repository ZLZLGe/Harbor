# Campaign Workbook Notes

The workbook contains a small synthetic store marketing experiment.

`ExposureSummary` columns:
- `WeekStart`: reporting week start date
- `StoreID`: store identifier
- `Region`: store region
- `CampaignGroup`: experiment arm assigned to the store
- `Visitors`: observed visitors during the campaign window
- `Purchasers`: number of visitors who placed at least one order
- `DisplayCost`: in-store display cost for context only; it is not needed for the output

`Orders` columns:
- `OrderID`: unique order identifier
- `StoreID`: store identifier
- `CampaignGroup`: experiment arm
- `Channel`: sales channel label
- `Revenue`: realized order revenue

Important relationships:
- Within each `CampaignGroup`, the number of `Orders` rows equals the total `Purchasers` from `ExposureSummary`
- `TotalRevenue` and all AOV statistics must be computed from `Orders`
- All lift metrics and confidence intervals are defined versus `Control`
