#!/bin/bash
set -euo pipefail

cat > /root/similar_fuzz.py <<'PY'
import sys
import atheris

with atheris.instrument_imports():
    from lineproto import parse_frame


@atheris.instrument_func
def TestOneInput(data):
    try:
        parse_frame(data)
    except Exception:
        return


atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
PY

cat > /root/similar_target_notes.md <<'EOF'
# Fuzz target notes

- target function: `lineproto.parse_frame`
- byte-oriented boundary: pipe-delimited frames with optional base64 payloads
- interesting branches: malformed field counts, bad lengths, base64 decoding, checksum handling, command payloads
EOF

python /root/similar_fuzz.py -atheris_runs=25 >/dev/null 2>/root/similar_fuzz.log
