# Campaign Attribution Dataset

Both inputs are gzipped CSV files without headers.

## Impression stream

File: `campaign_impressions.csv.gz`

Columns:

1. `event_time_micros`
2. `campaign_id`
3. `impression_id`
4. `user_id`
5. `creative_id`

Each row is a single impression event.

## Click stream

File: `campaign_clicks.csv.gz`

Columns:

1. `event_time_micros`
2. `campaign_id`
3. `impression_id`
4. `click_id`
5. `quality`

`quality=VALID` means the click is eligible for attribution. Other values should be ignored for attribution.

## Attribution rules

- Join on `(campaign_id, impression_id)`.
- A click only attributes if it is `VALID` and its event time is not earlier than the matched impression.
- If multiple valid clicks match an impression, keep the earliest valid click only.
- Unmatched clicks should not produce output.
- The final report is written after the bounded streams finish and the last watermark closes outstanding event-time state.
