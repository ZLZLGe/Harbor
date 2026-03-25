#!/usr/bin/env python3
import json
import sys

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def load_rows(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def fmt_int(value):
    return f"{value:,}"


def build_table(rows):
    header = ["SA2 Code", "SA2 Name", "State", "Population 2024", "Earners", "Median Income"]
    body = [
        [
            str(row["sa2_code"]),
            row["sa2_name"],
            row["state"],
            fmt_int(row["population_2024"]),
            fmt_int(row["earners"]),
            fmt_int(row["median_income"]),
        ]
        for row in rows
    ]
    table = Table([header] + body, repeatRows=1, colWidths=[22 * mm, 40 * mm, 18 * mm, 32 * mm, 26 * mm, 30 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e78")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (2, 0), (2, -1), "CENTER"),
                ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
            ]
        )
    )
    return table


def main():
    source_path, output_path = sys.argv[1], sys.argv[2]
    rows = load_rows(source_path)
    styles = getSampleStyleSheet()

    doc = SimpleDocTemplate(output_path, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm)
    story = [
        Paragraph("Regional Demographic Brief", styles["Title"]),
        Spacer(1, 4 * mm),
        Paragraph("Use the regional table below to prepare state-level demographic rollups.", styles["BodyText"]),
        Spacer(1, 6 * mm),
    ]

    chunk_size = 4
    for index in range(0, len(rows), chunk_size):
        if index:
            story.append(PageBreak())
            story.append(Paragraph(f"Regional Demographic Brief (continued {index // chunk_size + 1})", styles["Heading2"]))
            story.append(Spacer(1, 4 * mm))
        story.append(build_table(rows[index : index + chunk_size]))

    doc.build(story)


if __name__ == "__main__":
    main()
