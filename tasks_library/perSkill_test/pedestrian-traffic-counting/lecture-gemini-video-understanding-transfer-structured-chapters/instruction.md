## Task description

In `/app/lecture/raw`, I provide a classroom recording. Review the lecture video and produce a structured outline at `/app/lecture/chapter_outline.json`.

The output must be a JSON object with exactly these top-level fields:
- `video`: the source filename.
- `overall_summary`: one concise paragraph summarizing the lecture.
- `chapters`: an array of chapter objects sorted by time.

Each chapter object must contain exactly these fields:
- `start_time`: chapter start in `MM:SS`
- `end_time`: chapter end in `MM:SS`
- `title`: a short descriptive chapter title
- `mode`: one of these exact Chinese labels: `讲台讲解`, `白板书写`, `实物演示`, `问答`

Additional requirements:
- Use the single lecture file in `/app/lecture/raw`.
- Segment the whole lecture into chapters that cover the full recording in chronological order.
- Timestamps must align with visible topic changes in the recording.
- Keep `overall_summary` to one paragraph, with no bullet points.
- Do not add extra top-level fields or extra chapter fields.

The verifier will check the JSON structure, timestamp ordering, chapter labels, and whether the outline captures the key topics shown in the lecture.
