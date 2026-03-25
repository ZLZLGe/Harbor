There is a short tutorial excerpt at `/root/similar_excerpt.mp4`.

Generate `/root/similar_chapter_index.json` with this structure:

```json
{
  "clip_title": "Floor Plan Tutorial Excerpt A",
  "clip_duration_seconds": 205,
  "chapters": [
    {
      "time": 0,
      "title": "What we'll do"
    }
  ]
}
```

Use exactly these 7 chapter titles in this exact order:

1. What we'll do
2. How we'll get there
3. Getting a floor plan
4. Getting started
5. Basic Navigation
6. Import your plan into Blender
7. Basic transform operations

Requirements:

1. Output exactly 7 chapter entries.
2. The first chapter must start at `0`.
3. Timestamps must be strictly increasing.
4. Every timestamp must be between `0` and `205`.
5. Chapter titles must match the list above exactly.
6. Each timestamp should mark the first point where that topic begins in the excerpt.
