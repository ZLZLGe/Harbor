## Task description

In `/app/loading_dock`, I provide fixed-camera safety videos from a loading dock. Review every video file in that directory and identify every **near miss** where a forklift passes dangerously close to either a pedestrian or a handcart.

Use these rules:
- A near miss means the forklift and the other object come within obviously unsafe clearance, but there is no visible collision.
- Include only forklift interactions with a `pedestrian` or a `handcart`.
- Do not include routine traffic, distant crossings, or events that are not clearly hazardous.
- Use the timestamp of the closest approach, formatted as `MM:SS`.

Write the result to `/app/loading_dock/near_miss_timeline.json`.

The output must be a JSON array. Each item must be an object with exactly these fields:
- `video`: source filename
- `timestamp`: the near-miss time in `MM:SS`
- `objects`: an array of exactly two lowercase strings, sorted alphabetically, chosen from `forklift`, `pedestrian`, `handcart`
- `evidence`: one short sentence describing the visible cue that makes this a near miss

Sort the array by `video`, then by `timestamp`. Include one record for every near miss in the provided clips and no extra records.
