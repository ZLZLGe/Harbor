You are reviewing access-control traffic captured in `/root/pcaps/transfer1_badge_access.pcap`.

Produce this file in `/root/`:
1. `transfer1_badge_denials.json`

Only consider HTTP `POST` requests whose path is exactly `/badge/v1/swipe`.

For each considered request:
1. Parse `site`, `door`, and `badge` from the URI query string.
2. Parse `result` and `reason` from the URL-encoded request body.

Write a JSON object with these top-level keys:
1. `site`
2. `denied_count`
3. `doors`
4. `badges`
5. `events`

Rules:
1. Keep only requests whose body says `result=denied`.
2. `site` is the shared site value for the denied events.
3. `denied_count` is the number of denied events.
4. `doors` is an array of objects with keys `door` and `count`, sorted by `count` descending and then `door` ascending.
5. `badges` is the sorted list of unique denied badge IDs.
6. `events` is an array of objects with keys `frame_number`, `door`, `badge`, and `reason`, sorted by `frame_number` ascending.
