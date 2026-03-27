You are given three image panels and one manifest.

Input files:
1. `/root/image_manifest.json`
2. `/root/coin.png`
3. `/root/enemy.png`
4. `/root/turtle.png`

Create `/root/similar_counting_results.csv`.

Requirements:
1. Read frames in the exact order listed in `/root/image_manifest.json`.
2. For each frame, count how many `coin`, `enemy`, and `turtle` objects appear using the provided templates.
3. Write a CSV with exactly these columns in this order:
   - `frame_id`
   - `coins`
   - `enemies`
   - `turtles`
4. Use the absolute image path as `frame_id`.
5. Preserve manifest order in output rows.
6. Do not add extra columns or rows.
