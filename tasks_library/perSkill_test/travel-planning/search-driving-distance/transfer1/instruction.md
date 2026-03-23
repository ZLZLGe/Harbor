You are preparing a reimbursement sheet for same-day courier requests in Texas.

Input file in `/root/data/`:
1. `transfer1_courier_requests.csv`

Produce this file in `/root/`:
1. `transfer1_taxi_quote_sheet.csv`

Requirements:
1. Use the bundled city-to-city ground-distance lookup instead of memory.
2. Use taxi mode for every request.
3. Write a CSV with exactly these columns in this order:
   - `rank_by_quote`
   - `request_id`
   - `origin`
   - `destination`
   - `duration_minutes`
   - `distance_km`
   - `taxi_quote`
   - `within_budget`
4. `taxi_quote` must be the integer taxi estimate returned by the bundled lookup.
5. `within_budget` must be `yes` when `taxi_quote <= max_taxi_budget`, otherwise `no`.
6. Sort rows by `taxi_quote` ascending, breaking ties by `request_id`.
7. `rank_by_quote` must start at 1 and follow the sorted order.
