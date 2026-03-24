You are preparing a storyboard manifest for a short product demo clip stored at `/root/demo-clip.mp4`.

Requirements:

1. Extract every key frame from the video and save the images in timeline order under `/root/storyboard_frames/` using the exact filename pattern `scene_%03d.png`.
2. Create `/root/storyboard_manifest.csv` with exactly these columns in this order:
   - `frame_path`
   - `sequence`
   - `width`
   - `height`
   - `file_size_bytes`
3. `frame_path` must contain the absolute path for each saved image, such as `/root/storyboard_frames/scene_001.png`.
4. `sequence` must start at `1` and increase by `1` in timeline order.
5. `width` and `height` are the pixel dimensions of each extracted image.
6. `file_size_bytes` is the final file size of each extracted image in bytes.

Do not add extra columns, and make sure the CSV rows are sorted in the same order as the numbered image sequence.
