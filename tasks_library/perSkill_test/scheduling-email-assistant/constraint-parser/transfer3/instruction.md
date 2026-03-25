You are building a ledger of loading-dock booking constraints.

Input file in `/root/data/`:
1. `transfer3_loading_memos.md`

Produce this file in `/root/`:
1. `transfer3_loading_constraints.csv`

Requirements:
1. Write a CSV file with this header exactly:
   `vendor_id,vendor_name,arrival_dates,window_start,window_end,blocked_ranges,unload_minutes,notes`
2. Write one row per vendor memo in source order.
3. Join multiple dates with `|`.
4. Join multiple blocked ranges with `|`.
5. Keep the output values exactly as extracted and normalized from the bundled memos.
