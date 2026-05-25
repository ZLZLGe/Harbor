There is a tutorial video at `/root/tutorial_video.mp4`.

Generate `/root/tutorial_minute_cards.csv` with a minute-level timeline card.

CSV header must be exactly:

```csv
minute,second_mark,chapter_id,chapter_title
```

Rules:

1. Include one row for every full minute mark from 0 to 22 (23 rows total, excluding header).
2. `second_mark` must be `minute * 60`.
3. `chapter_id` and `chapter_title` must correspond to the chapter active at that second mark.
4. Rows must be sorted by `minute` ascending with no gaps.
5. `chapter_title` text must match canonical chapter names exactly.
