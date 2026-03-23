#!/bin/bash
set -euo pipefail

python3 <<'PY'
from pathlib import Path

sid = 2001001
parts = [
    'msg:"Export submit rule"',
    "flow:established,to_server",
    "http.method",
    'content:"POST"',
    "http.uri",
    'content:"/collect/v1/submit"',
    "http.header",
    'content:"X-Op-Mode|3a| sync"',
    "nocase",
    "http.request_body",
    'content:"payload="',
    'pcre:"/(?:^|&)payload=[A-Za-z0-9+\\\\/]{88,}={0,2}(?:&|$)/"',
    'pcre:"/(?:^|&)digest=[0-9a-fA-F]{40}(?:&|$)/"',
    f"sid:{sid}",
    "rev:1",
]
rule = "alert http any any -> any any (" + "; ".join(parts) + ";)\n"
Path("/root/similar.rules").write_text(rule, encoding="utf-8")
print(rule)
PY

tmpdir="/tmp/similar_oracle"
rm -rf "$tmpdir"
mkdir -p "$tmpdir/pos" "$tmpdir/neg"

suricata -c /root/suricata.yaml -S /root/similar.rules -k none -r /root/pcaps/train_pos.pcap -l "$tmpdir/pos" >/dev/null 2>&1
if ! grep -q '"signature_id":2001001' "$tmpdir/pos/eve.json"; then
  echo "expected sid 2001001 on train_pos.pcap" >&2
  exit 1
fi

suricata -c /root/suricata.yaml -S /root/similar.rules -k none -r /root/pcaps/train_neg.pcap -l "$tmpdir/neg" >/dev/null 2>&1
if grep -q '"signature_id":2001001' "$tmpdir/neg/eve.json"; then
  echo "unexpected sid 2001001 on train_neg.pcap" >&2
  exit 1
fi
