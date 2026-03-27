You are auditing HTTP telemetry traffic captured in `/root/pcaps/similar_telemetry.pcap`.

Produce this file in `/root/`:
1. `similar_request_audit.csv`

Include one row for every HTTP request whose path is exactly `/telemetry/v2/report`.

Write the CSV with this header:
`frame_number,src_ip,src_port,method,uri,tlm_mode,blob_length,sig_length,is_exfil_candidate`

Rules:
1. Sort rows by `frame_number` ascending.
2. `tlm_mode` is the `X-TLM-Mode` header value, trimmed and lowercased. Use an empty string if the header is missing.
3. Parse the request body as URL-encoded form data.
4. `blob_length` is the length of the top-level `blob` value. Use `0` when `blob` is absent.
5. `sig_length` is the length of the top-level `sig` value. Use `0` when `sig` is absent.
6. `is_exfil_candidate` must be `true` only when all of the following are true:
   - method is `POST`
   - `tlm_mode` equals `exfil`
   - `blob_length >= 80`
   - `sig_length == 64`
7. Write booleans as lowercase `true` or `false`.
