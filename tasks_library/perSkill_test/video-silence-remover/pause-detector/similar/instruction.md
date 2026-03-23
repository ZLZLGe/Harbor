A precomputed one-second energy timeline is provided at:

- `/root/data/similar_lecture_energies.json`

Create `/root/similar_pause_segments.json`.

Requirements:

1. Analyze the timeline from second `5` onward.
2. Treat low-energy periods as pauses using:
   - `threshold_ratio = 0.55`
   - `min_duration = 2`
   - `window_size = 5`
3. The output must be a JSON object with these fields:
   - `method`
   - `segments`
   - `total_segments`
   - `total_duration_seconds`
   - `parameters`
4. Each segment must contain `start`, `end`, and `duration` in seconds.
5. Keep numeric values as JSON numbers and keep segments in ascending time order.
