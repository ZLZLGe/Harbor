You are given 3 sprite images:
- `/root/coin.png`
- `/root/enemy.png`
- `/root/turtle.png`

Create `/root/mario_image_audit.csv` with columns:
`asset,width,height,mean_gray`

Process:
1. Create transformed grayscale variants (all exactly `48x48`):
   - coin -> grayscale + resize
   - enemy -> grayscale + resize + one contrast enhancement
   - turtle -> grayscale + resize + blur `0x1`
2. For each transformed variant, compute:
   - width
   - height
   - mean grayscale intensity in `[0, 255]`
3. Write one CSV row for each asset in this order: `coin`, `enemy`, `turtle`.
4. Format `mean_gray` with exactly two decimal places.

Rules:
- Output file path must be exactly `/root/mario_image_audit.csv`.
- Keep row order deterministic.
