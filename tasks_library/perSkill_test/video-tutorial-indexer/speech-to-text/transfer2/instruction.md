There is a later tutorial excerpt at `/root/transfer2_cleanup_clip.mp4`.

Create `/root/transfer2_stage_windows.md` as a markdown document with:

1. A first line exactly equal to `# Stage Windows`
2. A markdown table with this exact header row:

```text
| stage_key | label | start_seconds | end_seconds |
```

Use exactly these 6 ordered stage definitions:

1. `cleanup` -> `Remove unnecessary geometry`
2. `faces` -> `Make the floor's faces`
3. `background` -> `Make the background`
4. `extrude_z` -> `Extruding the walls in Z`
5. `orientation_review` -> `Reviewing face orientation`
6. `wall_thickness_modifiers` -> `Adding thickness to walls with Modifiers`

Requirements:

1. All timestamps must be measured relative to the beginning of this clip.
2. The stages must appear in the exact order above.
3. `start_seconds` must be strictly increasing.
4. Every `end_seconds` value must be greater than its corresponding `start_seconds`.
5. The final stage must end within the 193-second clip.
6. Each row should mark the span where that spoken stage runs in the clip.
