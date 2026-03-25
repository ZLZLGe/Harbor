You are drafting a market-spread audit memo from a bundled flight database.

Input file in `/root/data/`:
1. `transfer2_market_checks.json`

Produce this file in `/root/`:
1. `transfer2_market_report.md`

Requirements:
1. Use the bundled flight lookup data instead of memory.
2. Evaluate the listed markets in the same order as the input file.
3. For each market:
   - search the exact origin, destination, and flight date
   - if one or more flights exist, compute:
     - `flight_count`
     - `min_price`
     - `max_price`
     - `price_spread`
     - `cheapest_flight`
     - `cheapest_departure`
   - choose the cheapest flight by price, then earlier departure time, then flight number
4. For a market with no matching flights, mark it as `NO_SERVICE` and use `-` for the metric columns.
5. Write the markdown report using this exact structure:
   - `# Transfer 2 Market Report`
   - a blank line
   - a markdown table with columns:
     - `market_id`
     - `route`
     - `date`
     - `status`
     - `flight_count`
     - `min_price`
     - `max_price`
     - `price_spread`
     - `cheapest_flight`
     - `cheapest_departure`
   - a blank line
   - `## Summary`
   - a bullet `- Widest spread market: ...`
   - a bullet `- No-service markets: ...`
   - a bullet `- Tool called: search_flights`
6. The widest-spread summary must pick the available market with the largest `price_spread`.
7. For the no-service summary, list market IDs joined by `, `, or write `none` if every market has service.
