#!/bin/bash
set -euo pipefail

mkdir -p /root/workspace

python3 - <<'PY'
from pathlib import Path
import re

from pypdf import PdfReader, PdfWriter


data_dir = Path("/root/data")
order_path = data_dir / "assembly_order.txt"
output_path = Path("/root/workspace/site_packet.pdf")

step_pattern = re.compile(
    r"^\s*(\d+)\s*\|\s*([^|]+)\|\s*page\s+(\d+)\s*\|\s*rotate\s+(\d+)\s*$",
    re.IGNORECASE,
)

writer = PdfWriter()

for raw_line in order_path.read_text(encoding="utf-8").splitlines():
    line = raw_line.strip()
    if not line or line.startswith("#"):
        continue

    match = step_pattern.match(line)
    if not match:
        raise ValueError(f"无法解析装订步骤: {raw_line}")

    _, file_name, page_number, rotation = match.groups()
    pdf_path = data_dir / file_name.strip()
    reader = PdfReader(str(pdf_path))
    page = reader.pages[int(page_number) - 1]

    turn = int(rotation) % 360
    if turn:
        page.rotate(turn)

    writer.add_page(page)

with output_path.open("wb") as fh:
    writer.write(fh)
PY
