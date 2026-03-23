You are reviewing archive dispatch traffic hidden in HTTP form posts.

Files available in the container:
1. PCAPs in `/root/pcaps/`
2. Suricata config at `/root/suricata.yaml`
3. Starter rules file at `/root/transfer3.rules`

Update `/root/transfer3.rules` so that Suricata raises `sid:2001004` only when all of these conditions are true:
1. The request method is `POST`.
2. The request path is exactly `/dispatch/archive/push`.
3. A request header contains `X-Dispatch-Mode: archive`.
4. A request header contains `Content-Type: application/x-www-form-urlencoded`.
5. The request body has a top-level `chunk=` parameter whose value looks Base64-like and is at least 90 characters long.
6. The request body has a top-level `serial=` parameter whose value is exactly 12 decimal digits.

Requirements:
1. Avoid false positives on lookalike traffic in the bundled PCAPs.
2. Keep the output as valid Suricata rule text.
3. Do not change any file except `/root/transfer3.rules`.
