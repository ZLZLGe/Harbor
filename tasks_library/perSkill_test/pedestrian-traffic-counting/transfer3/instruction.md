A timeline event file is available at `/root/scene_alerts.json`.

Create `/root/transfer3_alerts.md` exactly in this markdown pattern:

```markdown
# Pedestrian Safety Alert Digest

## <video_name>
- total_events: <int>
- alert_events: <int>
- highest_waiting: <int> at <MM:SS>
- crossings_during_red: <int>
```

Rules:
1. Build one section per video sorted by video name ascending.
2. `alert_events` counts events where:
   - `pedestrians_waiting >= 10`, OR
   - `signal == RED` and `pedestrians_crossing > 0`.
3. `highest_waiting` uses max `pedestrians_waiting`; if tie, choose earliest timestamp.
4. `crossings_during_red` is the sum of `pedestrians_crossing` across RED-signal events.
5. Keep exact field names and section ordering as shown.
