Read the patient callback messages in `/root/patient_callbacks.json` and write a normalized follow-up scheduling summary to `/root/clinic_followup_constraints.json`.

The input file contains a top-level `callbacks` array. Each item includes `callback_id`, `patient_name`, `source_channel`, and `message_text`.

Write a JSON object with this exact top-level shape:

```json
{
  "callbacks": [
    {
      "callback_id": "string",
      "patient_name": "string",
      "visit_duration_minutes": 30,
      "allowed_days": ["Monday"],
      "preferred_visit_windows": [
        {
          "days": ["Monday"],
          "start_time": "08:00",
          "end_time": "11:00"
        }
      ],
      "no_visit_dates": [
        {
          "date": "YYYY-MM-DD",
          "reason": "string"
        }
      ],
      "timing_conditions": ["string"]
    }
  ]
}
```

Rules:
1. Use full English weekday names in `allowed_days`, sorted from Monday through Sunday.
2. Use 24-hour `HH:MM` for every time.
3. `visit_duration_minutes` must be an integer number of minutes.
4. Each `preferred_visit_windows` entry must use a `days` array plus one `start_time` and one `end_time`. Sort these entries by the first weekday they mention, then by `start_time`.
5. Each `no_visit_dates` entry must contain one `YYYY-MM-DD` date and a short reason taken from the message. Sort these entries by date ascending.
6. `timing_conditions` should contain concise complete sentences for explicit timing prerequisites or waiting rules mentioned in the message, such as fasting requirements or delays after treatment. If none are stated, use an empty array.
7. Sort the output `callbacks` array by `callback_id` in ascending order.
8. Output valid JSON only.
