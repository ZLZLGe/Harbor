Read the multi-page clinic capacity packet in `/root/clinic_capacity_packet.pdf` and create `/root/transfer2_capacity_flags.json`.

The output JSON must contain exactly these top-level keys:
- `district_utilization`
- `at_risk_clinics`
- `overflow_watchlist`

Requirements:
- Parse every table page in the PDF. The packet spans multiple pages and repeats the same columns.
- Treat each row as one clinic record with district, slot count, booked count, no-show count, and wait days.
- For `district_utilization`, aggregate by district and include `district`, `total_slots`, `total_booked`, `utilization_pct`, and `avg_wait_days`. Round percentage and average values to two decimals. Sort by `district`.
- For `at_risk_clinics`, include every clinic where utilization is at least `95.00` percent or `wait_days` is at least `12`. Each item must include `clinic_code`, `district`, `utilization_pct`, and `wait_days`. Sort by `clinic_code`.
- For `overflow_watchlist`, include each district where district-level utilization is at least `90.00` percent or district-level average wait days is at least `10.00`. Return the district names as a sorted list.

Save the final JSON to `/root/transfer2_capacity_flags.json`.
