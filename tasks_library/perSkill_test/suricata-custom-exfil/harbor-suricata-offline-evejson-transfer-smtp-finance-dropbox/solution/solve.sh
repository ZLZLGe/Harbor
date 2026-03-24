#!/bin/bash
set -euo pipefail

python3 <<'PY'
from pathlib import Path

SID = 2305001
REV = 1

parts = []
parts.append('msg:"SMTP quarterly finance archive delivery"')
parts.append("flow:established,to_server")
parts.append('content:"RCPT TO|3a|<dropbox@shadow.example>|0d 0a|"; nocase')
parts.append('content:"|0d 0a|Subject|3a 20|Quarterly Archive|0d 0a|"; nocase')
parts.append('content:"Content-Disposition|3a 20|attachment|3b|"; nocase')
parts.append('content:"Content-Transfer-Encoding|3a 20|base64|0d 0a|"; nocase')
parts.append(r'pcre:"/filename=\"finance-(?:19|20)\d{2}(?:0[1-9]|1[0-2])\.zip\"/Ri"')
parts.append(f"sid:{SID}")
parts.append(f"rev:{REV}")

rule = "alert tcp any any -> any 25 (" + "; ".join(parts) + ";)"
Path("/root/smtp_finance_drop.rules").write_text(rule + "\n")
print(rule)
PY

pos_dir="$(mktemp -d /tmp/smtp-finance-pos-XXXXXX)"
neg_dir="$(mktemp -d /tmp/smtp-finance-neg-XXXXXX)"

suricata -c /root/suricata.yaml -S /root/smtp_finance_drop.rules -k none -r /root/pcaps/train_pos.pcap -l "$pos_dir" >/dev/null 2>&1
if ! grep -q '"signature_id":2305001' "$pos_dir/eve.json"; then
  echo "expected sid 2305001 on train_pos.pcap" >&2
  exit 1
fi

suricata -c /root/suricata.yaml -S /root/smtp_finance_drop.rules -k none -r /root/pcaps/train_neg.pcap -l "$neg_dir" >/dev/null 2>&1
if grep -q '"signature_id":2305001' "$neg_dir/eve.json"; then
  echo "unexpected sid 2305001 on train_neg.pcap" >&2
  exit 1
fi
