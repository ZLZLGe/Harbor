You are auditing laboratory upload traffic captured in `/root/pcaps/transfer2_lab_uploads.pcap`.

Produce this file in `/root/`:
1. `transfer2_lab_upload_summary.md`

Only consider HTTP `PUT` requests whose path is exactly `/lab/v2/upload`.

For each considered request:
1. Parse `station` and `specimen` from the URI query string.
2. Parse `status` and `bytes` from the URL-encoded request body.

Write the markdown file with this exact structure:
1. First line: `# Lab Upload Summary`
2. Then `accepted_requests: <count>`
3. Then `rejected_requests: <count>`
4. Then a blank line
5. Then `## Station Totals`
6. Then one bullet per station with at least one accepted request in this form:
   `- <station>: <accepted_count> accepted, <accepted_bytes> bytes`
7. Then a blank line
8. Then `## Largest Accepted Upload`
9. Then these four lines:
   - `frame_number: <value>`
   - `station: <value>`
   - `specimen: <value>`
   - `bytes: <value>`

Rules:
1. Sort station bullets alphabetically by station name.
2. The largest accepted upload is chosen by highest `bytes`, breaking ties by lower `frame_number`.
