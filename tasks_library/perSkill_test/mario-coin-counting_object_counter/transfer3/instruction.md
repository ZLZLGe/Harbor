You are given three image panels and one manifest.

Input files:
1. `/root/image_manifest.json`
2. `/root/coin.png`
3. `/root/enemy.png`
4. `/root/turtle.png`

Create `/root/transfer3_ranked_scoreboard.tsv`.

Rules:
1. Read frames in manifest order and count coins, enemies, turtles for each frame.
2. Compute `score = coins * 2 + enemies * 3 + turtles * 4`.
3. Assign severity bucket:
   - `critical` if score >= 10
   - `medium` if score >= 4 and < 10
   - `low` otherwise
4. Sort rows by score descending, then by frame_id ascending.
5. Write TSV columns in this exact order:
   - rank
   - frame_id
   - coins
   - enemies
   - turtles
   - score
   - bucket
