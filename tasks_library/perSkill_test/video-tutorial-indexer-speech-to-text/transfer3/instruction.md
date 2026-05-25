There is a tutorial video at `/root/tutorial_video.mp4`.

Generate `/root/chapter_duration_leaderboard.json`.

Required format:

```json
{
  "video_info": {
    "title": "In-Depth Floor Plan Tutorial Part 1",
    "duration_seconds": 1382
  },
  "top_longest_chapters": [
    {
      "rank": 1,
      "chapter_id": 15,
      "chapter_title": "Continue tracing inner walls",
      "start_time": 628,
      "end_time": 864,
      "duration_seconds": 236
    }
  ]
}
```

Requirements:

1. Include exactly 10 chapters in `top_longest_chapters`.
2. Sort by `duration_seconds` descending; ties broken by smaller `chapter_id` first.
3. `rank` must be 1 through 10 in order.
4. `duration_seconds` must equal `end_time - start_time`.
5. All chapter fields must be consistent with the inferred chapter timeline.
