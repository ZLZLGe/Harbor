Read the inbound demo request emails in `/root/demo_requests.json` and write a normalized scheduling digest to `/root/demo_request_constraints.json`.

The input file contains a top-level `requests` array. Each item includes `request_id`, `from_email`, `subject`, and `email_text`.

Write a JSON object with this exact top-level shape:

```json
{
  "requests": [
    {
      "request_id": "string",
      "requester_email": "string",
      "timezone_reference": "string",
      "session_duration_minutes": 45,
      "acceptable_date_ranges": [
        {
          "start_date": "YYYY-MM-DD",
          "end_date": "YYYY-MM-DD"
        }
      ],
      "preferred_time_windows": [
        {
          "start_date": "YYYY-MM-DD",
          "end_date": "YYYY-MM-DD",
          "start_time": "HH:MM",
          "end_time": "HH:MM"
        }
      ],
      "blackout_periods": [
        {
          "start_date": "YYYY-MM-DD",
          "end_date": "YYYY-MM-DD",
          "start_time": "HH:MM or null",
          "end_time": "HH:MM or null",
          "note": "string"
        }
      ]
    }
  ]
}
```

Rules:
1. Use `YYYY-MM-DD` for every date.
2. Use 24-hour `HH:MM` for every time.
3. Preserve the timezone reference as a concise label directly supported by the email text.
4. If a blackout covers a whole day, set `start_time` and `end_time` to `null`.
5. If a request has no blackout periods, use an empty array.
6. Sort the output `requests` array by `request_id` in ascending order.
7. Output valid JSON only.
