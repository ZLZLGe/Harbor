You are inspecting digest batch traffic captured in `/root/pcaps/transfer3_digest_batches.pcap`.

Produce this file in `/root/`:
1. `transfer3_digest_fingerprints.tsv`

Only consider HTTP `POST` requests whose path is exactly `/digest/v1/batch`.

For each considered request:
1. Parse `lane` and `batch` from the URI query string.
2. Parse the request body as newline-delimited `key=value` lines.
3. Extract `sha256` and `records` from the body.

Write a TSV file with this header:
`frame_number	lane	batch	records	sha256_prefix`

Rules:
1. `sha256_prefix` is the first 12 characters of the `sha256` value.
2. Sort rows by `lane` ascending, then `batch` ascending.
