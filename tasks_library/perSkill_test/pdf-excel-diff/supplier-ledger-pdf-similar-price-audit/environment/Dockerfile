FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY assets /tmp/build_assets

# Copy skills to agent-specific locations
COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

RUN pip3 install --break-system-packages \
    pandas==2.2.3 \
    pdfplumber==0.11.4 \
    reportlab==4.2.5

RUN python3 - <<'PY'
import csv
import shutil
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle

assets_dir = Path("/tmp/build_assets")
archive_csv = assets_dir / "archive_rows.csv"
current_csv = assets_dir / "current_prices.csv"
pdf_path = Path("/root/supplier_ledger_archive.pdf")
target_csv = Path("/root/supplier_prices_current.csv")

with archive_csv.open(newline="") as handle:
    reader = csv.reader(handle)
    rows = list(reader)

styles = getSampleStyleSheet()
doc = SimpleDocTemplate(
    str(pdf_path),
    pagesize=landscape(letter),
    leftMargin=24,
    rightMargin=24,
    topMargin=28,
    bottomMargin=24,
)

table = LongTable(
    rows,
    repeatRows=1,
    colWidths=[64, 132, 86, 48, 54, 64, 56, 48],
)
table.setStyle(
    TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9EAF4")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("LEADING", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
    )
)

story = [
    Paragraph("Archived Supplier Ledger", styles["Title"]),
    Spacer(1, 8),
    table,
]
doc.build(story)

shutil.copyfile(current_csv, target_csv)
shutil.rmtree(assets_dir)
PY
