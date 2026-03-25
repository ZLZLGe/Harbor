You are given a CSV of museum exhibit stops at `/root/exhibit_packet/stops.csv`.

Produce a zipped stop-audio pack for the gallery floor.

Requirements:

1. Read the CSV in row order and keep that order in the packaged manifest.
2. Create `/root/exhibit-stop-pack.zip`.
3. The zip file must contain exactly these items at its root:
   - `manifest.json`
   - one MP3 per CSV row, named `<stop_id>.mp3`
4. `manifest.json` must be valid UTF-8 JSON containing an array of objects in CSV order. Each object must have exactly these keys:
   - `stop_id`
   - `title`
   - `audio_file`
   - `duration_hint_seconds`
   - `spoken_text`
5. For each manifest entry:
   - `audio_file` must equal `<stop_id>.mp3`
   - `duration_hint_seconds` must match the CSV value
   - `spoken_text` must equal `Stop <stop_id>. <title>. <narration>` using the exact narration text from the CSV with no summarization or rewriting
6. Each MP3 must be playable and must contain a full spoken reading of its `spoken_text`.
7. Each stop audio should stay reasonably close to its duration hint, within about 12 seconds of the CSV value.

Notes:

- You may use local or remote speech synthesis, but the task must finish inside the container.
- The verifier will inspect the zip contents, compare the packaged manifest against the CSV, and transcribe each MP3 to confirm it speaks the packaged `spoken_text` rather than silence or unrelated audio.
