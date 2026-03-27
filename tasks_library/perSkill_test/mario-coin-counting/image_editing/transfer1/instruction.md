You are given 3 sprite images:
- `/root/coin.png`
- `/root/enemy.png`
- `/root/turtle.png`

Create an atlas image at `/root/mario_icon_atlas.png`.

Required workflow:
1. Build three normalized images, each exactly `64x64` and grayscale.
2. Apply these per-image transforms before atlas composition:
   - coin: grayscale + resize only.
   - enemy: grayscale + vertical flip + resize.
   - turtle: grayscale + horizontal flip + resize.
3. Concatenate the three normalized images horizontally in this exact order:
   coin, enemy, turtle.
4. Save the result as `/root/mario_icon_atlas.png`.

Rules:
- Keep deterministic geometry and order.
- Do not add text overlays or borders.
