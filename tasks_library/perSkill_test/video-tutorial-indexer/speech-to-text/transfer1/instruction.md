There is a narrated tutorial audio excerpt at `/root/transfer1_trace_audio.mp3`.

Create `/root/transfer1_cue_sheet.csv` with this exact header:

```text
cue_title,start_seconds,end_seconds,duration_seconds
```

Use exactly these 5 cue titles in this exact order:

1. Tracing inner walls
2. Break
3. Continue tracing inner walls
4. Remove doubled vertices
5. Save

Requirements:

1. The timestamps must be measured relative to the beginning of this audio excerpt, not the full original tutorial.
2. Output exactly 5 rows after the header.
3. `start_seconds`, `end_seconds`, and `duration_seconds` must be numeric.
4. `start_seconds` must be strictly increasing.
5. Each row should mark the span where that spoken section runs in the audio excerpt.
6. The final row must end within the 331-second excerpt.
