Pilot line final-test engineers and burn-in technicians are writing mixed Chinese-English failure notes during a pre-release cleanup run. The notes are short, noisy, and sometimes contain two independent clues in one sentence. Your task is to normalize those remarks into the standard product reason codebooks and write the result to `/app/output/final_test_reason_map.json`.

Input files are stored in `/app/data/`:
- `pilot_line_events.jsonl`: one JSON object per event.
- `reason_codebooks.json`: product-specific standard reason entries and station scopes.

Generate a JSON object with this format:

```json
{
  "records": [
    {
      "event_id": "",
      "product_id": "",
      "station": "",
      "engineer_id": "",
      "test_item": "",
      "symptom_code": "",
      "raw_reason_text": "",
      "reason_segments": [
        {
          "segment_id": "",
          "span_text": "",
          "pred_code": "",
          "pred_label": "",
          "confidence": 0.0,
          "rationale": ""
        }
      ]
    }
  ]
}
```

Requirements:
- `segment_id` must be `<event_id>-S<i>` starting from 1 within each event.
- `span_text` must be an exact substring copied from `raw_reason_text`.
- Notes may contain multiple independent clauses; split them into segments when needed, but preserve exact substrings.
- `pred_code` and `pred_label` must come from the matching product codebook.
- Respect `station_scope`. If a code is not valid for the event station, do not use it.
- When evidence is weak or ambiguous, set `pred_code` to `"UNKNOWN"` and `pred_label` to `""`.
- `confidence` must be a numeric value in `[0.0, 1.0]`, rounded to 4 decimals, and known mappings should generally be more confident than `UNKNOWN`.
- `rationale` should be short but concrete, citing useful evidence such as station, symptom code, test item, tokens, or component hints.

Write only the required JSON output file.
