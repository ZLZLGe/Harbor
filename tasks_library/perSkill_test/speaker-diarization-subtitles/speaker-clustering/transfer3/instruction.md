A retake session has already been split into short speaking windows in:

- `/root/data/studio_retakes.jsonl`

Each JSON line includes:

- `segment_id`
- `start_ms`
- `end_ms`
- `signature`

Use the signature vectors to assign stable speaker labels, then merge consecutive windows from the same speaker whenever the gap is `<= 0.12` seconds.

Write `/root/output/transfer3_session_brief.md` with:

- the total speaker count
- the merged turn count
- one section per speaker in first-seen order
- each speaker section must include total duration and the merged time ranges

Use the label format `speaker_01`, `speaker_02`, ...
