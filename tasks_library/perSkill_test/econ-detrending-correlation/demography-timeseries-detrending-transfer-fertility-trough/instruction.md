Demographers often compare observed fertility rates with their long-run trend to see when childbearing is unusually weak relative to structural conditions. In this task you will work with an annual U.S.-style panel that has already been assembled.

Goal: Using `/root/fertility_inputs.csv`, construct the annual general fertility rate for 1970 through 2024, remove its long-run trend, and identify the year with the most negative cyclical gap.

The CSV has one row per year with these columns:
- `year`
- `births`
- `women_15_44`
- `registration_coverage`
- `series_status`

Requirements:
1. Use all rows in the file, covering 1970 to 2024.
2. Construct the annual general fertility rate as:
   - `general_fertility_rate = births / women_15_44 * 1000`
3. The resulting series is already an annual rate, so apply the Hodrick-Prescott filter directly to that rate series in levels.
4. Use `lambda = 100`, the standard smoothing parameter for annual data.
5. Find the year with the minimum cyclical component.
6. Write `/root/fertility-cycle-trough.csv` as a one-row CSV with exactly these columns:
   - `year`
   - `cycle_gap`
7. `cycle_gap` must be the cyclical component for the trough year, expressed in births per 1,000 women and rounded to 5 decimal places.

Example output:
```csv
year,cycle_gap
2023,-1.23456
```
