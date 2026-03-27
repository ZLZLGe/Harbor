Split `/root/input.mp4` into a three-part prep package and document it.

Requirements:
1. Create these files:
   - `/root/transfer2_part_1.mp4` for 0.000s to 4.000s
   - `/root/transfer2_part_2.mp4` for 4.000s to 8.000s
   - `/root/transfer2_part_3.mp4` for 8.000s to 12.000s
2. Create `/root/transfer2_split_map.json` describing all three parts.
3. The JSON must include, for each part: `file`, `start_sec`, and `duration_sec`.
4. Keep video playable and preserve original frame size.
