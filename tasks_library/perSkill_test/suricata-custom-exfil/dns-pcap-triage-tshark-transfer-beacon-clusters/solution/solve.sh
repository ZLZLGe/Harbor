#!/bin/bash
set -euo pipefail

tshark -r /root/pcaps/dns_resolver_mix.pcap \
  -Y 'dns && dns.flags.response == 0' \
  -T fields \
  -E separator=/t \
  -E quote=n \
  -e frame.time_epoch \
  -e ip.src \
  -e dns.qry.type \
  -e dns.qry.name > /tmp/dns_queries.tsv

python3 <<'PY'
import csv
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


INPUT = Path("/tmp/dns_queries.tsv")
OUTPUT = Path("/root/dns_beacon_clusters.csv")


def normalize_name(value: str) -> str:
    return value.strip().rstrip(".").lower()


def base_domain(name: str) -> str:
    labels = name.split(".")
    return ".".join(labels[-2:])


groups: dict[tuple[str, str], list[tuple[float, str]]] = defaultdict(list)

for raw_line in INPUT.read_text().splitlines():
    if not raw_line.strip():
        continue
    parts = raw_line.split("\t")
    if len(parts) != 4:
        continue
    ts_raw, src_host, qtype, qname_raw = parts
    if qtype != "1":
        continue
    qname = normalize_name(qname_raw)
    if not qname:
        continue
    groups[(src_host, base_domain(qname))].append((float(ts_raw), qname))


rows = []
for (src_host, domain), entries in groups.items():
    entries.sort(key=lambda item: item[0])
    if len(entries) < 4:
        continue

    qname_lengths = [len(qname) for _, qname in entries]
    if any(length < 45 for length in qname_lengths):
        continue

    gaps = [entries[idx + 1][0] - entries[idx][0] for idx in range(len(entries) - 1)]
    if any(gap < 50 or gap > 80 for gap in gaps):
        continue

    first_seen = datetime.fromtimestamp(entries[0][0], tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows.append(
        {
            "src_host": src_host,
            "suspicious_base_domain": domain,
            "query_count": str(len(entries)),
            "longest_query_name_len": str(max(qname_lengths)),
            "first_seen_utc": first_seen,
        }
    )

rows.sort(key=lambda row: (row["first_seen_utc"], row["src_host"]))

with OUTPUT.open("w", newline="") as fh:
    writer = csv.DictWriter(
        fh,
        fieldnames=[
            "src_host",
            "suspicious_base_domain",
            "query_count",
            "longest_query_name_len",
            "first_seen_utc",
        ],
    )
    writer.writeheader()
    writer.writerows(rows)
PY
