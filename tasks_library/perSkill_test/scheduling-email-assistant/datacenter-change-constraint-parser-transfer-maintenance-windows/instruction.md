Read the datacenter maintenance approval threads in `/root/maintenance_threads.json` and write a normalized timing-constraint summary to `/root/change_window_constraints.json`.

The input file contains a top-level `changes` array. Each item includes `change_id`, `system`, `region`, and `approval_thread`. Each `approval_thread` entry contains `author`, `role`, `posted_at`, and `body`.

Write a JSON object with this exact top-level shape:

```json
{
  "changes": [
    {
      "change_id": "string",
      "system": "string",
      "approved_windows": [
        {
          "start_date": "YYYY-MM-DD",
          "end_date": "YYYY-MM-DD",
          "start_time": "HH:MM",
          "end_time": "HH:MM",
          "timezone": "string"
        }
      ],
      "freeze_periods": [
        {
          "start_date": "YYYY-MM-DD",
          "end_date": "YYYY-MM-DD",
          "reason": "string"
        }
      ],
      "prohibited_dates": [
        {
          "date": "YYYY-MM-DD",
          "reason": "string"
        }
      ],
      "maximum_outage_minutes": 30,
      "sequencing_constraints": ["string"]
    }
  ]
}
```

Rules:
1. Include only windows that are explicitly approved in the thread. Do not keep tentative proposals that were later rejected or superseded.
2. Use `YYYY-MM-DD` for every date and 24-hour `HH:MM` for every time.
3. Each `approved_windows` item must cover one contiguous approved maintenance window. Sort these entries by `start_date`, then `start_time`.
4. `freeze_periods` should contain only explicit freeze ranges or no-change ranges that span one or more full dates. Sort them by `start_date`.
5. `prohibited_dates` should contain explicit single blocked dates that are not already represented by a freeze period. Sort them by `date`.
6. `maximum_outage_minutes` must be an integer number of minutes.
7. `sequencing_constraints` should be concise complete sentences describing explicit ordering requirements from the thread. Preserve multiple requirements when they are stated. Keep them in the same order they appear in the approved guidance.
8. Sort the output `changes` array by `change_id` in ascending order.
9. Output valid JSON only.
