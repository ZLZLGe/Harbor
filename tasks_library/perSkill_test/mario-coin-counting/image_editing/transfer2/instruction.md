You are given 3 sprite images at `/root/coin.png`, `/root/enemy.png`, and `/root/turtle.png`.

Create a preview GIF at `/root/mario_skill_preview.gif`.

Steps:
1. Generate six `80x80` frames from those sprites in this exact order:
   1) coin grayscale
   2) enemy grayscale
   3) turtle grayscale
   4) coin grayscale + negate
   5) enemy grayscale + edge detection with radius 1
   6) turtle grayscale + blur `0x1`
2. Assemble the six frames into a looping GIF.
3. Use a constant per-frame delay so playback is stable.

Rules:
- Output file path must be exactly `/root/mario_skill_preview.gif`.
- Frame ordering must match the listed sequence.
- Every frame must be `80x80`.
