In `/app/workspace/` I provided a Flink job skeleton together with a small synthetic ad-attribution dataset.

The input files are:

- `/app/workspace/data/campaign_impressions.csv.gz`
- `/app/workspace/data/campaign_clicks.csv.gz`
- `/app/workspace/data/schema_notes.md`

The event timestamps are in microseconds.

## Task

In `/app/workspace/src/main/java/campaignaudit/query/CampaignAttributionLagAudit.java`, implement a Flink job that audits attribution lag per campaign.

An impression is identified by `(campaignId, impressionId)`.

For each impression:

1. Match clicks from the click stream using the same `(campaignId, impressionId)`.
2. Only clicks with `quality=VALID` are eligible.
3. A click only counts if its event time is greater than or equal to the matched impression event time.
4. If multiple eligible clicks match one impression, keep only the earliest eligible click.
5. If no eligible click ever matches that impression before the final watermark closes, that impression is unattributed.

After all event-time work is finished, output one summary line per campaign with:

- the number of unattributed impressions
- the P95 of valid attribution lag in microseconds

Use the nearest-rank definition for P95: sort the valid lags for that campaign ascending and take the element at index `ceil(0.95 * n)`. If a campaign has no valid attributed impressions, write `-1` for the P95 field.

Ignore clicks that do not have a matching impression, clicks for the wrong campaign, invalid clicks, and clicks that occur before the matched impression in event time.

Line order is not important.

## Output

Write `/app/workspace/campaign_attribution_sla.txt` with one line per campaign in this exact format:

`campaign=<campaignId> unattributed=<count> p95_valid_click_lag_micros=<p95>`

## Input Parameters

- `impression_input`: path to a single gzipped impression CSV file
- `click_input`: path to a single gzipped click CSV file
- `output`: path to the output file

## Provided Code

- `/app/workspace/src/main/java/campaignaudit/query/CampaignAttributionLagAudit.java`: provided Flink job skeleton. Do not change the class name.
- `/app/workspace/src/main/java/campaignaudit/utils/AppBase.java`: base helpers already provided.
- `pom.xml`: defines the job class and jar name. Do not change this file.

You may add supporting classes under `campaignaudit.datatypes`, `campaignaudit.sources`, and `campaignaudit.utils` if needed.
