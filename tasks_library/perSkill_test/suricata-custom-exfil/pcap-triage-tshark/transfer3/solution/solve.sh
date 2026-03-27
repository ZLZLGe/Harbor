#!/bin/bash
set -euo pipefail

python3 <<'PY'
from pathlib import Path

from pcap_http_utils import parse_key_value_lines, parse_query_params, read_http_requests


pcap_path = Path("/root/pcaps/transfer3_digest_batches.pcap")
output_path = Path("/root/transfer3_digest_fingerprints.tsv")

rows = []
for request in read_http_requests(pcap_path):
    if request.method != "POST" or request.path != "/digest/v1/batch":
        continue
    query = parse_query_params(request.uri)
    kv = parse_key_value_lines(request.body_text)
    rows.append(
        {
            "frame_number": request.frame_number,
            "lane": query["lane"],
            "batch": query["batch"],
            "records": kv["records"],
            "sha256_prefix": kv["sha256"][:12],
        }
    )

rows = sorted(rows, key=lambda item: (item["lane"], item["batch"]))
lines = ["frame_number\tlane\tbatch\trecords\tsha256_prefix"]
for row in rows:
    lines.append(f"{row['frame_number']}\t{row['lane']}\t{row['batch']}\t{row['records']}\t{row['sha256_prefix']}")

output_path.write_text("\n".join(lines) + "\n")
PY
