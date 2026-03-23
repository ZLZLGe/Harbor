You are reviewing HTTP snapshot upload traffic.

Files available in the container:
1. PCAPs in `/root/pcaps/`
2. Suricata config at `/root/suricata.yaml`
3. Starter rules file at `/root/transfer1.rules`

Update `/root/transfer1.rules` so that Suricata raises `sid:2001002` only when all of these conditions are true:
1. The request method is `PUT`.
2. The request path is exactly `/snapshot/api/v1/upload`.
3. A request header contains `X-Archive-Intent: mirror`.
4. A request header contains `Content-Type: application/json`.
5. The JSON request body contains `"batch":"nightly"`.
6. The JSON request body contains a `"payload"` value that looks Base64-like and is at least 96 characters long.
7. The JSON request body contains a `"sha256"` value that is exactly 64 hexadecimal characters.

Requirements:
1. Avoid false positives on lookalike traffic in the bundled PCAPs.
2. Keep the output as valid Suricata rule text.
3. Do not change any file except `/root/transfer1.rules`.
