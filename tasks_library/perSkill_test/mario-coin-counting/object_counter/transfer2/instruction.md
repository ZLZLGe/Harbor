You are given three image panels and one manifest.

Input files:
1. `/root/image_manifest.json`
2. `/root/coin.png`
3. `/root/enemy.png`
4. `/root/turtle.png`

Create `/root/transfer2_shift_report.md`.

Rules:
1. Read frames in manifest order and compute counts for coins, enemies, and turtles.
2. For each frame compute `risk_score = coins * 1 + enemies * 2 + turtles * 3`.
3. Write markdown in this exact structure:

```markdown
# Template Presence Report

| frame_id | coins | enemies | turtles | risk_score |
|---|---:|---:|---:|---:|
| ... | ... | ... | ... | ... |

Highest risk frame: <frame_path>
```

4. Table rows must keep manifest order.
5. If risk ties, `Highest risk frame` must pick the first row in table order.
