A timeline export is available at `/root/minute_events.json`.

Create `/root/transfer1_timeline.json` in this exact schema:

```json
{
  "generated_at": "static",
  "videos": [
    {
      "video": "...",
      "peak_minute": "MM",
      "unique_pedestrians": 0,
      "top_zone": "..."
    }
  ]
}
```

Rules:
1. Use only events where `actor_type == "pedestrian"`.
2. `peak_minute` is the minute (`MM`) with the highest number of unique `track_id` values within that minute.
3. If multiple minutes tie for `peak_minute`, choose the earliest minute.
4. `unique_pedestrians` is unique `track_id` count for the whole video.
5. `top_zone` is the zone with most pedestrian events in the whole video.
6. If zones tie, pick lexicographically smallest zone.
7. Sort `videos` by `video` ascending.
