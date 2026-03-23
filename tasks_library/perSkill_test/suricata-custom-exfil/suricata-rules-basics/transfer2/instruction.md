You are reviewing staged pull traffic hidden in HTTP requests.

Files available in the container:
1. PCAPs in `/root/pcaps/`
2. Suricata config at `/root/suricata.yaml`
3. Starter rules file at `/root/transfer2.rules`

Update `/root/transfer2.rules` so that Suricata raises `sid:2001003` only when all of these conditions are true:
1. The request method is `GET`.
2. The request URI starts with `/cdn/diag/pull?`.
3. A request header contains `X-Pull-Mode: stage`.
4. The URI contains a top-level `node=` parameter with exactly 8 hexadecimal characters.
5. The URI contains a top-level `ticket=` parameter with exactly 12 decimal digits.

Requirements:
1. Avoid false positives on lookalike traffic in the bundled PCAPs.
2. Keep the output as valid Suricata rule text.
3. Do not change any file except `/root/transfer2.rules`.
