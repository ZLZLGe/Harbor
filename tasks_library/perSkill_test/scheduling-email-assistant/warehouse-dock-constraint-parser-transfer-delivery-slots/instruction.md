Read the warehouse dock scheduling messages in `/root/dock_messages.json` and write a normalized dock appointment summary to `/root/dock_slot_constraints.json`.

The input file contains a top-level `loads` array. Each item includes `load_id`, `carrier_name`, `warehouse_code`, `commodity`, and `message_bundle`. Each `message_bundle` entry contains `speaker`, `role`, `sent_at`, and `text`.

Write a JSON object with this exact top-level shape:

```json
{
  "loads": [
    {
      "load_id": "string",
      "carrier_name": "string",
      "required_slot_length_minutes": 90,
      "arrival_windows": [
        {
          "start_date": "YYYY-MM-DD",
          "end_date": "YYYY-MM-DD",
          "start_time": "HH:MM",
          "end_time": "HH:MM"
        }
      ],
      "no_arrival_intervals": [
        {
          "start_date": "YYYY-MM-DD",
          "end_date": "YYYY-MM-DD",
          "start_time": "HH:MM",
          "end_time": "HH:MM",
          "reason": "string"
        }
      ],
      "date_flexibility": "string",
      "same_day_unloading_cutoff": {
        "time": "HH:MM",
        "condition": "string"
      }
    }
  ]
}
```

Rules:
1. Use `YYYY-MM-DD` for every date and 24-hour `HH:MM` for every time.
2. Include only the arrival windows that remain valid after the warehouse guidance in the message bundle. Do not keep earlier proposals that were explicitly rejected or replaced.
3. Each `arrival_windows` item must represent one contiguous appointment window. Sort these entries by `start_date`, then `start_time`.
4. Each `no_arrival_intervals` item must represent one explicit blocked interval inside an otherwise allowed receiving period. Sort these entries by `start_date`, then `start_time`.
5. `required_slot_length_minutes` must be an integer number of minutes.
6. `date_flexibility` must be one concise complete sentence describing how fixed or movable the receiving date is, using exact ISO dates where the messages support them.
7. `same_day_unloading_cutoff.time` must be the explicit cutoff time for same-day unloading. `same_day_unloading_cutoff.condition` must be one concise complete sentence describing what happens when a truck arrives after that cutoff.
8. Sort the output `loads` array by `load_id` in ascending order.
9. Output valid JSON only.
