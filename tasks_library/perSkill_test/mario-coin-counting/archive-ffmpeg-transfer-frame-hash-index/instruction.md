You are preparing a frame hash index for the archive surveillance clip stored at `/root/archive-camera.mp4`.

Requirements:

1. Extract every key frame from the video in timeline order and save the images under `/root/archive_keyframes/` using the exact filename pattern `archive_%04d.png`.
2. Create `/root/frame_hash_index.tsv`.
3. The file must be tab-separated text with a trailing newline.
4. The first row must be the header with exactly these columns in this order:
   - `frame_path`
   - `sequence`
   - `sha256`
5. `frame_path` must be the absolute path of the extracted image, such as `/root/archive_keyframes/archive_0001.png`.
6. `sequence` must start at `1` and increase by `1` in timeline order.
7. `sha256` must be the lowercase SHA256 hash of the exact extracted image file bytes stored on disk.
8. Include one data row for every extracted key frame, with no extra columns and no skipped frames.
