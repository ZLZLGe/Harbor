Read the multi-page regional demographic packet in `/root/demographic_brief.pdf` and create `/root/similar_demographic_summary.json`.

The output JSON must contain exactly these top-level keys:
- `state_population_totals`
- `state_earner_totals`
- `state_region_counts`
- `state_income_quartile_earners`
- `top_total_regions`

Requirements:
- Parse every table page in the PDF. The packet spans multiple pages and repeats the same columns.
- Treat the PDF columns as regional records with state, population, earners, and median income values.
- For `state_population_totals`, sum population by state and sort the list by `state`.
- For `state_earner_totals`, sum earners by state and sort the list by `state`.
- For `state_region_counts`, count the number of regions per state and sort the list by `state`.
- For `state_income_quartile_earners`, assign each region to quartiles `Q1` through `Q4` using the full-set distribution of `median_income`, then report earners summed by `state` and `quartile`. Include every state and every quartile, using `0` where a state has no regions in a quartile. Sort by `state`, then `quartile`.
- For `top_total_regions`, compute `total = earners * median_income`, then return the top three regions sorted by descending `total` and then ascending `sa2_code`. Each item must include `sa2_code`, `sa2_name`, `state`, and `total`.

Save the final JSON to `/root/similar_demographic_summary.json`.
