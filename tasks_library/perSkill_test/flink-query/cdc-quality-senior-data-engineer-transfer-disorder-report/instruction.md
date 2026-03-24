In `/app/workspace/` I provided a Flink job skeleton together with a small synthetic healthcare CDC dataset.

The input files are:

- `/app/workspace/data/disorder_cdc_events.csv.gz`
- `/app/workspace/data/schema_notes.md`

The single CDC file is already in ingestion order. Each record also carries its event timestamp in UTC.

## Task

In `/app/workspace/src/main/java/cdcquality/query/CdcDisorderQualityReport.java`, implement a Flink job that builds a daily CDC quality report from one multi-table change stream.

Each input record represents one CDC change event and includes:

- `table_name`
- `primary_key`
- `change_seq`
- `event_time_utc`
- `operation`

Use `(table_name, primary_key)` as the entity key.

Process the CDC records in ingestion order with these rules:

1. Keep exactly one retained record per entity key: the event with the highest `change_seq` seen for that key.
2. If an event arrives with the same `change_seq` as the current retained record for that key, suppress it as a duplicate event.
3. If an event arrives with a smaller `change_seq` than the current retained record for that key, count it as an out-of-order update and do not let it replace the retained record.
4. If an event arrives with a larger `change_seq`, it becomes the new retained record for that key.

Build one output line per `(date, table_name)`, where `date` is the UTC calendar date derived from `event_time_utc`.

For each `(date, table_name)`, output:

- `duplicate_suppressed`: how many suppressed duplicate events happened on that date for that table
- `out_of_order_updates`: how many out-of-order events happened on that date for that table
- `final_retained_records`: after the full input is consumed, how many final retained records belong to that same date and table, using the retained record's own `event_time_utc`

Additional rules:

- A later retained record can move an entity from one report date to another. The final report must reflect only the final retained version for that entity key.
- `DELETE` records are still valid retained CDC records if they are the latest version for that key.
- Only emit lines for `(date, table_name)` combinations where at least one of the three output metrics is non-zero.
- Line order is not important.

## Output

Write `/app/workspace/cdc_quality_report.txt` with one line per `(date, table_name)` in this exact format:

`date=<YYYY-MM-DD> table=<table_name> duplicate_suppressed=<count> out_of_order_updates=<count> final_retained_records=<count>`

## Input Parameters

- `cdc_input`: path to the single gzipped CDC CSV file
- `output`: path to the output file

## Provided Code

- `/app/workspace/src/main/java/cdcquality/query/CdcDisorderQualityReport.java`: provided Flink job skeleton. Do not change the class name.
- `/app/workspace/src/main/java/cdcquality/utils/AppBase.java`: base helpers already provided.
- `pom.xml`: defines the job class and jar name. Do not change this file.

You may add supporting classes under `cdcquality.datatypes`, `cdcquality.sources`, and `cdcquality.utils` if needed.
