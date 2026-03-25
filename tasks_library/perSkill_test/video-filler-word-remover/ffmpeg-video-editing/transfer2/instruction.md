A source briefing video is at `/root/transfer2_source.mp4`.

Chapter anchors are provided in:

- `/root/data/transfer2_chapters.json`

Create these outputs in `/root/`:

1. `transfer2_sampler_manifest.csv`
2. `transfer2_sampler_reel.mp4`
3. directory `transfer2_clips/` with one clip per chapter row kept in the manifest

Rules:

1. For each chapter, extract a teaser clip from `start` to `start + 2.4` seconds.
2. If a chapter starts after the video ends, skip it.
3. If `start + 2.4` exceeds video duration, truncate to video end.
4. Concatenate all teaser clips in manifest order into `transfer2_sampler_reel.mp4`.
5. `transfer2_sampler_manifest.csv` must use this header exactly:
   - `clip_name,chapter_id,topic,start,end,clip_duration`
6. Numeric fields in CSV must use three decimal places.
