You are given 3 sprite images:
- `/root/coin.png`
- `/root/enemy.png`
- `/root/turtle.png`

Create a four-panel grayscale strip at `/root/mario_keyframe_strip.png`.

Required workflow:
1. Build four `64x64` grayscale panels in this exact order:
   1) coin (grayscale + resize)
   2) enemy (grayscale + resize)
   3) turtle (grayscale + resize)
   4) coin (grayscale + negate + resize)
2. Concatenate the four panels horizontally into one output image.
3. Save the final image to `/root/mario_keyframe_strip.png`.

Rules:
- Keep panel order fixed.
- Do not add text, borders, or extra spacing.
