You are filling an operations handoff manifest with exact-match flight information.

Input file in `/root/data/`:
1. `transfer1_manifest_requests.csv`

Produce this file in `/root/`:
1. `transfer1_manifest.csv`

Requirements:
1. Use the bundled flight lookup data instead of memory.
2. Keep the output rows in the same order as the input rows.
3. For each request, search the exact origin, destination, and flight date.
4. If one or more matching flights exist:
   - set `status` to `AVAILABLE`
   - choose the cheapest flight
   - break price ties by earlier departure time, then by flight number
5. If no matching flight exists:
   - set `status` to `NO_SERVICE`
   - leave the selected flight fields empty
6. Write a CSV with this exact header:
   - `request_id`
   - `priority`
   - `status`
   - `origin`
   - `destination`
   - `flight_date`
   - `selected_flight_number`
   - `selected_price`
   - `selected_departure`
   - `selected_arrival`
   - `tool_called`
7. Set `tool_called` to `search_flights` for every row.
