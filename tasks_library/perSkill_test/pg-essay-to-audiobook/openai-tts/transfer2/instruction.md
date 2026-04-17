Build one reminder-call audio batch from `/root/data/call_snippets.csv`.

Input:
- `/root/data/call_snippets.csv`
- `/root/data/task_config.json`

Save:
- `/root/transfer2_call_batch.flac`
- `/root/transfer2_call_batch_report.json`

Requirements:
- process every CSV row in file order
- each row must become one spoken segment in the combined output
- report must include `rows_processed`, `priority_counts`, `voice`, `model`, and `total_duration_sec`
- `priority_counts` must include all priority levels that appear in the input
