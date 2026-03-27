#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
from collections import Counter
from pathlib import Path

from pcap_http_utils import parse_form_body, parse_query_params, read_http_requests


pcap_path = Path("/root/pcaps/transfer1_badge_access.pcap")
output_path = Path("/root/transfer1_badge_denials.json")

events = []
for request in read_http_requests(pcap_path):
    if request.method != "POST" or request.path != "/badge/v1/swipe":
        continue
    query = parse_query_params(request.uri)
    form = parse_form_body(request.body_text)
    if form.get("result") != "denied":
        continue
    events.append(
        {
            "frame_number": request.frame_number,
            "door": query["door"],
            "badge": query["badge"],
            "reason": form["reason"],
            "site": query["site"],
        }
    )

door_counts = Counter(event["door"] for event in events)
site = events[0]["site"] if events else ""
result = {
    "site": site,
    "denied_count": len(events),
    "doors": [{"door": door, "count": count} for door, count in sorted(door_counts.items(), key=lambda item: (-item[1], item[0]))],
    "badges": sorted({event["badge"] for event in events}),
    "events": [
        {
            "frame_number": event["frame_number"],
            "door": event["door"],
            "badge": event["badge"],
            "reason": event["reason"],
        }
        for event in sorted(events, key=lambda item: item["frame_number"])
    ],
}

output_path.write_text(json.dumps(result, indent=2) + "\n")
PY
