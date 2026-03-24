Open the provided workbook in the working directory. It contains four sheets:

- `Tariff Review`: finish all requested output cells here
- `MeterData`: time-band meter readings for each building
- `Rates`: tariff rates by plan and time band
- `Budget`: monthly building budgets and shiftable peak shares

Your goal is to complete the campus tariff review workbook without changing the layout or workbook structure.

1. Fill `F8:H17` on `Tariff Review`.
- `Meter kWh`: pull the matching reading from `MeterData`
- `Rate`: pull the matching tariff from `Rates`
- `Energy Cost`: multiply the reading by the rate

Each lookup row must match the month, building, meter ID, tariff plan, and time band already shown on `Tariff Review`.

2. Fill `B23:I27` on `Tariff Review` for the five listed buildings.
- `Peak Cost`: sum only the peak-band energy cost for that building
- `Valley Cost`: sum only the valley-band energy cost for that building
- `Total Cost`: peak cost plus valley cost
- `Budget`: pull the building budget from `Budget`
- `Variance`: total cost minus budget
- `Shiftable Peak Share`: pull the building share from `Budget`
- `Saveable Amount`: peak-band kWh multiplied by shiftable peak share and by the difference between the peak and valley rates
- `Action`: use exactly `Act Now` when both variance is positive and saveable amount is at least `300`; otherwise use `Plan Shift` when saveable amount is at least `200`; otherwise use `Track`

3. Fill `J32:N35` using the rank numbers already listed in `I32:I35`.
- Return the top 4 buildings ranked by `Saveable Amount`, from largest to smallest
- Fill `Building`, `Total Cost`, `Variance`, `Saveable Amount`, and `Action`

Requirements:

- Use formulas, not hard-coded final numbers
- Do not use macros or VBA
- Keep sheet names, formatting, and workbook structure unchanged
- Leave the completed workbook saved in place with the same filename
