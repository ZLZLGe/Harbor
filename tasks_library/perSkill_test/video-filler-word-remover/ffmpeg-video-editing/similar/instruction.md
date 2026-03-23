A source interview video is available at `/root/similar_source.mp4`.

Window annotations are provided in:

- `/root/data/similar_filler_windows.json`

Create these outputs in `/root/`:

1. `similar_filler_montage.mp4`
2. `similar_filler_windows_report.json`

Requirements:

1. Use every window from the JSON file.
2. Keep windows in ascending `start` order.
3. Extract each window as an individual clip and concatenate them into `similar_filler_montage.mp4`.
4. `similar_filler_windows_report.json` must be a JSON object with fields:
   - `source_video`
   - `output_video`
   - `segments_used`
   - `total_segments`
   - `total_duration_seconds`
5. `total_duration_seconds` must equal the sum of `(end - start)` over all used windows.
