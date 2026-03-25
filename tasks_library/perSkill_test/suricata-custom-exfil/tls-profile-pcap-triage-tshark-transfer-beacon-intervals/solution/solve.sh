#!/bin/bash
set -euo pipefail

INPUT="/workspace/inputs/tls_handshake_mix.pcap"
OUTPUT="/workspace/outputs/tls_beacon_profile.json"
TMP="$(mktemp)"

mkdir -p /workspace/outputs

tshark \
  -r "$INPUT" \
  -n \
  -o tcp.desegment_tcp_streams:true \
  -o tls.desegment_ssl_records:true \
  -Y 'tls.handshake.type == 1 && ip.src && ip.dst && tcp.dstport && tls.handshake.extensions_server_name' \
  -T fields \
  -e frame.time_epoch \
  -e ip.src \
  -e ip.dst \
  -e tcp.dstport \
  -e tls.handshake.extensions_server_name \
  -E header=n \
  -E separator='|' \
  > "$TMP"

python3 - "$TMP" "$OUTPUT" <<'PY'
from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path


input_path = Path(sys.argv[1])
output_path = Path(sys.argv[2])
groups: dict[tuple[str, str, int, str], list[float]] = defaultdict(list)

for raw_line in input_path.read_text().splitlines():
    if not raw_line.strip():
        continue
    parts = raw_line.split("|")
    if len(parts) != 5:
        continue
    ts_text, src, dst, dport_text, sni = parts
    sni = sni.strip()
    if not sni:
        continue
    groups[(src, dst, int(dport_text), sni)].append(float(ts_text))

beacons = []
for (src, dst, dport, sni), times in groups.items():
    times.sort()
    if len(times) < 5:
        continue
    deltas = [round(times[idx + 1] - times[idx]) for idx in range(len(times) - 1)]
    period = round(statistics.median(deltas))
    if any(abs(delta - period) > 3 for delta in deltas):
        continue
    evidence = f"{len(times)} handshakes; intervals={deltas}; median period {period}s"
    beacons.append(
        {
            "client_ip": src,
            "target_ip": dst,
            "target_port": dport,
            "sni": sni,
            "connection_count": len(times),
            "approx_period_seconds": period,
            "evidence": evidence,
        }
    )

beacons.sort(key=lambda item: (item["client_ip"], item["target_ip"], item["target_port"], item["sni"]))
output_path.write_text(json.dumps({"beacons": beacons}, indent=2) + "\n")
PY

rm -f "$TMP"
