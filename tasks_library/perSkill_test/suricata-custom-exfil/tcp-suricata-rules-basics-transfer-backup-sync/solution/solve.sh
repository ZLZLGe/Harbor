#!/bin/bash
set -euo pipefail

python3 <<'PY'
from pathlib import Path


SID = 1000001
REV = 1

parts = [
    'msg:"TCP backup sync mirror detected"',
    "flow:to_server,established,only_stream",
    'content:"SYNC/3"',
    'content:"MODE|3a 20|MIRROR"',
    'content:"DEST|3a 20|vault"',
    'content:"PAYLOAD="',
    'content:"TOKEN="',
    r'pcre:"/(?:^|\r?\n)SYNC\/3(?:\r?\n|$)/s"',
    r'pcre:"/(?:^|\r?\n)MODE:\x20MIRROR(?:\r?\n|$)/s"',
    r'pcre:"/(?:^|\r?\n)DEST:\x20vault(?:\r?\n|$)/s"',
    r'pcre:"/(?:^|\r?\n)PAYLOAD=[0-9A-Fa-f]{128,}(?:\r?\n|$)/s"',
    r'pcre:"/(?:^|\r?\n)TOKEN=[0-9A-Fa-f]{32}(?:\r?\n|$)/s"',
    f"sid:{SID}",
    f"rev:{REV}",
]

rule = "alert tcp any any -> any 4040 (" + "; ".join(parts) + ";)"
Path("/root/tcp_backup_sync.rules").write_text(rule + "\n")
print(rule)
PY

tmpdir="$(mktemp -d /tmp/tcp_backup_sync_oracle.XXXXXX)"
mkdir -p "$tmpdir/pos" "$tmpdir/neg"

suricata -c /root/suricata.yaml -S /root/tcp_backup_sync.rules -k none -r /root/pcaps/backup_match.pcap -l "$tmpdir/pos" >/dev/null 2>&1
if ! grep -q '"signature_id":1000001' "$tmpdir/pos/eve.json"; then
    echo "Oracle sanity-check failed on backup_match.pcap" >&2
    exit 1
fi

suricata -c /root/suricata.yaml -S /root/tcp_backup_sync.rules -k none -r /root/pcaps/backup_benign.pcap -l "$tmpdir/neg" >/dev/null 2>&1
if grep -q '"signature_id":1000001' "$tmpdir/neg/eve.json"; then
    echo "Oracle sanity-check failed on backup_benign.pcap" >&2
    exit 1
fi

echo "Oracle sanity-check passed."
