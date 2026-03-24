# Public Service Request Input Assets

This directory contains three synthetic but realistic service-request feeds that mimic:

- a city 311 intake export
- a campus maintenance queue
- a residential property work-order workbook

The task is to normalize heterogeneous issue hierarchies into one shared 4-level taxonomy suitable for dispatch analytics and SLA monitoring.

## Files

- `city311_service_requests.csv`
  - 18 rows
  - delimiter: ` > `
- `campus_maintenance_queue.jsonl`
  - 18 rows
  - delimiter: ` / `
- `residential_portfolio_work_orders.xlsx`
  - 18 rows
  - delimiter: ` :: `

The three sources intentionally contain equivalent issues with different naming styles, including graffiti cleanup, elevator outages, active leaks, hot water loss, no-cooling events, and lighting failures.
