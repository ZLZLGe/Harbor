You are investigating suspicious HTTP export traffic.

Files available in the container:
1. PCAPs in `/root/pcaps/`
2. Suricata config at `/root/suricata.yaml`
3. Starter rules file at `/root/similar.rules`

Update `/root/similar.rules` so that Suricata raises `sid:2001001` only when all of these conditions are true:
1. The request method is `POST`.
2. The request path is exactly `/collect/v1/submit`.
3. A request header contains `X-Op-Mode: sync`.
4. The request body has a top-level `payload=` parameter whose value looks Base64-like and is at least 88 characters long.
5. The request body has a top-level `digest=` parameter whose value is exactly 40 hexadecimal characters.

Requirements:
1. Avoid false positives on lookalike traffic in the bundled PCAPs.
2. Keep the output as valid Suricata rule text.
3. Do not change any file except `/root/similar.rules`.
