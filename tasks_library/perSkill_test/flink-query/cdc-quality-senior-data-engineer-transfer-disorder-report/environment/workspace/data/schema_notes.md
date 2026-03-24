# disorder_cdc_events.csv.gz

The file is a single bounded CDC stream for a healthcare analytics pipeline.

## Columns

1. `event_time_utc`: UTC timestamp in ISO-8601 format for the CDC event itself
2. `table_name`: logical source table name
3. `primary_key`: primary key value inside that table
4. `change_seq`: monotonically increasing source change sequence for one entity key
5. `operation`: CDC operation type such as `UPSERT`, `UPDATE`, or `DELETE`
6. `payload`: opaque payload fragment included only as background context

## Semantics

- The file order is the CDC ingestion order and should be treated as authoritative.
- `(table_name, primary_key)` identifies one entity key.
- A duplicate retransmission repeats the current retained `change_seq` for that key.
- An out-of-order update arrives after a newer `change_seq` was already observed for that key.
- Final retained record counts are grouped by the retained record's own event date and table, not by the date when earlier versions first appeared.
