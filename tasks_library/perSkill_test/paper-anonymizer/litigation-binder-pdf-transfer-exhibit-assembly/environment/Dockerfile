FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    wget \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages \
    pymupdf==1.24.0 \
    pypdf==4.0.0

COPY exhibit_seed_a.pdf exhibit_seed_b.pdf exhibit_seed_c.pdf /tmp/exhibit_seeds/

# Codex
COPY skills /root/.codex/skills

RUN python3 - <<'PY'
from pathlib import Path

from pypdf import PdfReader, PdfWriter


seed_dir = Path("/tmp/exhibit_seeds")
case_dir = Path("/root/case_files")
case_dir.mkdir(parents=True, exist_ok=True)

specs = [
    ("exhibit_a_operations_memo.pdf", "exhibit_seed_a.pdf", {2: 90}),
    ("exhibit_b_email_chain.pdf", "exhibit_seed_b.pdf", {4: 270}),
    ("exhibit_c_billing_backup.pdf", "exhibit_seed_c.pdf", {3: 180}),
]

for output_name, seed_name, rotations in specs:
    reader = PdfReader(str(seed_dir / seed_name))
    writer = PdfWriter()
    for index, page in enumerate(reader.pages):
        angle = rotations.get(index, 0)
        if angle:
            page.rotate(angle)
        writer.add_page(page)
    writer.add_metadata({"/Title": output_name})
    with (case_dir / output_name).open("wb") as handle:
        writer.write(handle)
PY

RUN mkdir -p /root/output

WORKDIR /root
