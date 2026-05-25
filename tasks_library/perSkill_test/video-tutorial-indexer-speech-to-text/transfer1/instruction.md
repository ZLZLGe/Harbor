There is a tutorial video at `/root/tutorial_video.mp4`.

Generate `/root/tutorial_phase_timeline.json` as a compact phase timeline (not full 29-chapter output).

Required format:

```json
{
  "video_info": {
    "title": "In-Depth Floor Plan Tutorial Part 1",
    "duration_seconds": 1382
  },
  "phases": [
    {
      "phase_id": "phase_1",
      "phase_title": "Orientation and Setup",
      "start_time": 0,
      "end_time": 126,
      "chapter_span": [1, 5]
    }
  ]
}
```

Use exactly these 8 phases in this exact order:

1. Orientation and Setup
2. Plan Import and Alignment
3. Wall Tracing Pass 1
4. Break and Tracing Resume
5. Geometry Cleanup and Floor
6. Wall Extrusion
7. Face Orientation Repair
8. Wrap-Up and Export

Requirements:

1. Exactly 8 phases.
2. `phase_id` must be `phase_1` ... `phase_8` in order.
3. `chapter_span` must be a two-item integer array `[start_chapter_id, end_chapter_id]`.
4. `start_time` and `end_time` must be numeric and strictly increasing by phase.
5. Phase boundaries must stay within 0 to 1382 seconds.
6. `video_info.title` and `video_info.duration_seconds` must match the required values exactly.
