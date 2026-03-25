There is a short closing audio excerpt at `/root/transfer3_closeout_audio.wav`.

Create `/root/transfer3_closeout_schedule.tsv` with this exact header:

```text
card_id	label	start_seconds	seconds_until_next
```

Use exactly these 4 ordered markers:

1. `face_orientation_note` -> `Note on face orientation`
2. `save_as` -> `Save As`
3. `mixed_wall_types` -> `If you need thick and thin walls`
4. `great_job` -> `Great job!`

Requirements:

1. All timestamps must be measured relative to the beginning of this audio excerpt.
2. Output exactly 4 rows after the header.
3. `start_seconds` must be strictly increasing.
4. `seconds_until_next` must be numeric and positive for every row.
5. The final row must still fit inside the 96-second excerpt.
6. Each row should mark the first point where that closing marker begins in the audio.
