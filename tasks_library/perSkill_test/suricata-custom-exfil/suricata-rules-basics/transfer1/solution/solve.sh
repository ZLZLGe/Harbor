#!/bin/bash
set -euo pipefail

python3 <<'PY'
from pathlib import Path

sid = 2001002
parts = [
    'msg:"Mirror snapshot rule"',
    "flow:established,to_server",
    "http.method",
    'content:"PUT"',
    "http.uri",
    'content:"/snapshot/api/v1/upload"',
    "http.header",
    'content:"X-Archive-Intent|3a| mirror"',
    "nocase",
    "http.header",
    'content:"Content-Type|3a| application/json"',
    "nocase",
    "http.request_body",
    'pcre:"/\\"batch\\"\\s*:\\s*\\"nightly\\"/"',
    'pcre:"/\\"payload\\"\\s*:\\s*\\"[A-Za-z0-9+\\\\/]{96,}={0,2}\\"/"',
    'pcre:"/\\"sha256\\"\\s*:\\s*\\"[0-9a-fA-F]{64}\\"/"',
    f"sid:{sid}",
    "rev:1",
]
rule = "alert http any any -> any any (" + "; ".join(parts) + ";)\n"
Path("/root/transfer1.rules").write_text(rule, encoding="utf-8")
print(rule)
PY

tmpdir="/tmp/transfer1_oracle"
rm -rf "$tmpdir"
mkdir -p "$tmpdir/pos" "$tmpdir/neg"

suricata -c /root/suricata.yaml -S /root/transfer1.rules -k none -r /root/pcaps/train_pos.pcap -l "$tmpdir/pos" >/dev/null 2>&1
if ! grep -q '"signature_id":2001002' "$tmpdir/pos/eve.json"; then
  echo "expected sid 2001002 on train_pos.pcap" >&2
  exit 1
fi

suricata -c /root/suricata.yaml -S /root/transfer1.rules -k none -r /root/pcaps/train_neg.pcap -l "$tmpdir/neg" >/dev/null 2>&1
if grep -q '"signature_id":2001002' "$tmpdir/neg/eve.json"; then
  echo "unexpected sid 2001002 on train_neg.pcap" >&2
  exit 1
fi
