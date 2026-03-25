You are given a local flashcard deck in `/root/review_cards/session.json`.

Produce a loop-friendly spoken review drill from that deck.

Requirements:

1. Read the cards in their JSON array order and keep that order in every output.
2. Create `/root/review-drill-session.wav`.
3. Create `/root/review-drill-timeline.json`.
4. For each card, speak exactly these two lines, with no paraphrasing or summarization:
   - `Question <index>. <prompt>`
   - `Answer <index>. <answer>`
5. Insert a fully silent think gap after each question. Its duration must match that card's `think_seconds` value from the source JSON.
6. Insert a fully silent reset gap of `0.75` seconds after each answer, including the final answer, so the track can loop cleanly.
7. `review-drill-timeline.json` must be valid UTF-8 JSON with exactly these top-level keys:

```json
{
  "session_title": "string",
  "cards": []
}
```

8. Each object in `cards` must contain exactly these keys:
   - `card_id`
   - `question_text`
   - `answer_text`
   - `think_seconds`
   - `reset_seconds`
   - `question_start_sec`
   - `question_end_sec`
   - `think_start_sec`
   - `think_end_sec`
   - `answer_start_sec`
   - `answer_end_sec`
   - `reset_start_sec`
   - `reset_end_sec`
9. In the timeline:
   - `question_text` must equal `Question <index>. <prompt>`
   - `answer_text` must equal `Answer <index>. <answer>`
   - timestamps must be numeric, strictly nondecreasing, and aligned with the WAV within `0.15` seconds
10. The WAV must be playable PCM audio and contain the full drill in the same card order as the timeline.

Notes:

- You may use local or remote speech synthesis, but the task must finish inside the container.
- The verifier will compare the timeline against the source JSON and inspect the WAV for real silent pause spans plus non-silent spoken spans.
