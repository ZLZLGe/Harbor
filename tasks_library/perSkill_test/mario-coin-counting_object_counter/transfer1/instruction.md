You are given three image panels and one manifest.

Input files:
1. `/root/image_manifest.json`
2. `/root/coin.png`
3. `/root/enemy.png`
4. `/root/turtle.png`

Create `/root/transfer1_presence_summary.json`.

Required JSON schema:
```json
{
  "scenario": "template_presence_audit",
  "frame_order": ["/root/coin.png", "/root/enemy.png", "/root/turtle.png"],
  "totals": {"coins": 0, "enemies": 0, "turtles": 0},
  "max_enemy_frame": {"frame_id": "...", "enemies": 0},
  "nonzero_turtle_frames": ["..."]
}
```

Rules:
1. Compute all counts from the manifest-listed frames using the three templates.
2. `frame_order` must preserve manifest order.
3. `max_enemy_frame` must pick the highest `enemies` value; break ties by first appearance in manifest order.
4. `nonzero_turtle_frames` contains frame paths where turtle count > 0, preserving manifest order.
