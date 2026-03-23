#!/bin/bash
set -euo pipefail

python3 <<'PY'
from pathlib import Path

sid = 2001003
parts = [
    'msg:"Stage pull rule"',
    "flow:established,to_server",
    "http.method",
    'content:"GET"',
    "http.uri",
    'content:"/cdn/diag/pull?"',
    'pcre:"/(?:^|[?&])node=[0-9a-fA-F]{8}(?:&|$)/"',
    'pcre:"/(?:^|[?&])ticket=[0-9]{12}(?:&|$)/"',
    "http.header",
    'content:"X-Pull-Mode|3a| stage"',
    "nocase",
    f"sid:{sid}",
    "rev:1",
]
rule = "alert http any any -> any any (" + "; ".join(parts) + ";)\n"
Path("/root/transfer2.rules").write_text(rule, encoding="utf-8")
print(rule)
PY

tmpdir="/tmp/transfer2_oracle"
rm -rf "$tmpdir"
mkdir -p "$tmpdir/pos" "$tmpdir/neg"

suricata -c /root/suricata.yaml -S /root/transfer2.rules -k none -r /root/pcaps/train_pos.pcap -l "$tmpdir/pos" >/dev/null 2>&1
if ! grep -q '"signature_id":2001003' "$tmpdir/pos/eve.json"; then
  echo "expected sid 2001003 on train_pos.pcap" >&2
  exit 1
fi

suricata -c /root/suricata.yaml -S /root/transfer2.rules -k none -r /root/pcaps/train_neg.pcap -l "$tmpdir/neg" >/dev/null 2>&1
if grep -q '"signature_id":2001003' "$tmpdir/neg/eve.json"; then
  echo "unexpected sid 2001003 on train_neg.pcap" >&2
  exit 1
fi
