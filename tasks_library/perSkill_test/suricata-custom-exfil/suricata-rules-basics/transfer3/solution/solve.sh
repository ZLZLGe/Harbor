#!/bin/bash
set -euo pipefail

python3 <<'PY'
from pathlib import Path

sid = 2001004
parts = [
    'msg:"Archive dispatch rule"',
    "flow:established,to_server",
    "http.method",
    'content:"POST"',
    "http.uri",
    'content:"/dispatch/archive/push"',
    "http.header",
    'content:"X-Dispatch-Mode|3a| archive"',
    "nocase",
    "http.header",
    'content:"Content-Type|3a| application/x-www-form-urlencoded"',
    "nocase",
    "http.request_body",
    'content:"chunk="',
    'pcre:"/(?:^|&)chunk=[A-Za-z0-9+\\\\/]{90,}={0,2}(?:&|$)/"',
    'pcre:"/(?:^|&)serial=[0-9]{12}(?:&|$)/"',
    f"sid:{sid}",
    "rev:1",
]
rule = "alert http any any -> any any (" + "; ".join(parts) + ";)\n"
Path("/root/transfer3.rules").write_text(rule, encoding="utf-8")
print(rule)
PY

tmpdir="/tmp/transfer3_oracle"
rm -rf "$tmpdir"
mkdir -p "$tmpdir/pos" "$tmpdir/neg"

suricata -c /root/suricata.yaml -S /root/transfer3.rules -k none -r /root/pcaps/train_pos.pcap -l "$tmpdir/pos" >/dev/null 2>&1
if ! grep -q '"signature_id":2001004' "$tmpdir/pos/eve.json"; then
  echo "expected sid 2001004 on train_pos.pcap" >&2
  exit 1
fi

suricata -c /root/suricata.yaml -S /root/transfer3.rules -k none -r /root/pcaps/train_neg.pcap -l "$tmpdir/neg" >/dev/null 2>&1
if grep -q '"signature_id":2001004' "$tmpdir/neg/eve.json"; then
  echo "unexpected sid 2001004 on train_neg.pcap" >&2
  exit 1
fi
