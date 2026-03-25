A word-level transcript export is provided at:

- `/root/data/similar_transcript_words.json`

Create `/root/similar_annotations.json` as a JSON array of filler detections.

Detect these filler words and phrases (case-insensitive):

- `um`, `uh`, `hum`, `hmm`, `mhm`
- `like`
- `you know`
- `i mean`
- `yeah`
- `so`
- `kind of`
- `basically`
- `i guess`
- `well`
- `okay`

Rules:

1. Input entries contain `word`, `start`, and `end` in seconds.
2. Use `start` as the detection timestamp.
3. For phrase fillers (`you know`, `i mean`, `kind of`, `i guess`), detect adjacent words in sequence.
4. Output each detection as `{"word": <normalized filler>, "timestamp": <seconds>}`.
5. Round timestamps to 2 decimals.
6. Sort detections by timestamp ascending.
7. Remove exact duplicates by `(word, timestamp)`.
