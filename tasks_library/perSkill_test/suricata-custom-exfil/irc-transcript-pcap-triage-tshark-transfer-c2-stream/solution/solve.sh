#!/usr/bin/env bash
set -euo pipefail

INPUT_PCAP="/workspace/inputs/irc_mix.pcap"
OUTPUT_FILE="/workspace/outputs/irc_c2_transcript.txt"
TMP_TSV="$(mktemp)"

mkdir -p /workspace/outputs

tshark -r "$INPUT_PCAP" \
  -Y 'tcp.port == 6667 && tcp.len > 0' \
  -T fields \
  -E separator=$'\t' \
  -e frame.time_epoch \
  -e tcp.stream \
  -e ip.src \
  -e ip.dst \
  -e tcp.payload > "$TMP_TSV"

python3 - "$TMP_TSV" "$OUTPUT_FILE" <<'PY'
from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


rows_path = Path(sys.argv[1])
output_path = Path(sys.argv[2])

buffers: dict[tuple[int, str, str], bytes] = defaultdict(bytes)
messages: dict[int, list[tuple[float, str, str, str]]] = defaultdict(list)

for raw_line in rows_path.read_text().splitlines():
    parts = raw_line.split("\t")
    if len(parts) != 5:
        continue
    epoch_text, stream_text, src_ip, dst_ip, payload_hex = parts
    if not payload_hex:
        continue

    key = (int(stream_text), src_ip, dst_ip)
    chunk = bytes.fromhex(payload_hex)
    data = buffers[key] + chunk
    while b"\r\n" in data:
        line_bytes, data = data.split(b"\r\n", 1)
        text = line_bytes.decode("utf-8", errors="replace")
        messages[key[0]].append((float(epoch_text), src_ip, dst_ip, text))
    buffers[key] = data

request_re = re.compile(r"^PRIVMSG\s+(\S+)\s+:(!.*)$")
response_re = re.compile(r"^:([^! ]+)![^ ]+\s+PRIVMSG\s+(\S+)\s+:(.+)$")

candidates: list[tuple[int, int, int]] = []
for stream, items in messages.items():
    command_count = 0
    response_count = 0
    for _epoch, _src, _dst, text in items:
        if request_re.match(text):
            command_count += 1
        if response_re.match(text):
            response_count += 1
    if command_count and response_count:
        candidates.append((command_count + response_count, command_count, stream))

if not candidates:
    raise SystemExit("no IRC command/response candidates found")

_score, _commands, chosen_stream = max(candidates)
chosen_messages = sorted(messages[chosen_stream], key=lambda item: item[0])

command_targets = [request_re.match(text).group(1) for _epoch, _src, _dst, text in chosen_messages if request_re.match(text)]
if not command_targets:
    raise SystemExit("no command target in chosen stream")
bot_nick = Counter(command_targets).most_common(1)[0][0]

response_targets = [
    response_re.match(text).group(2)
    for _epoch, _src, _dst, text in chosen_messages
    if response_re.match(text) and response_re.match(text).group(1) == bot_nick
]
if not response_targets:
    raise SystemExit("no bot replies in chosen stream")
controller_nick = Counter(response_targets).most_common(1)[0][0]

lines: list[str] = []
for epoch, _src, _dst, text in chosen_messages:
    request_match = request_re.match(text)
    if request_match and request_match.group(1) == bot_nick:
        direction = "controller->bot"
        message = request_match.group(2)
    else:
        response_match = response_re.match(text)
        if not response_match:
            continue
        if response_match.group(1) != bot_nick or response_match.group(2) != controller_nick:
            continue
        direction = "bot->controller"
        message = response_match.group(3)

    stamp = datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines.append(f"{stamp} | {direction} | {message}")

output_path.write_text("\n".join(lines) + "\n")
PY

rm -f "$TMP_TSV"
