#!/bin/bash
set -euo pipefail

cat > /tmp/generate_incident_briefing.py <<'PY'
#!/usr/bin/env python3

import json
from collections import Counter, defaultdict
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    LongTable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

INPUT_JSON = Path("/root/incident_data.json")
OUTPUT_PDF = Path("/root/incident_briefing_report.pdf")
OPEN_STATUSES = {"Active", "Monitoring", "Mitigated"}
SEVERITY_RANK = {"SEV-1": 0, "SEV-2": 1, "SEV-3": 2}


def load_data():
    with INPUT_JSON.open() as handle:
        return json.load(handle)


def compute_metrics(incidents):
    open_incidents = [item for item in incidents if item["status"] in OPEN_STATUSES]
    resolved_incidents = [item for item in incidents if item["status"] == "Resolved"]
    total_customers = sum(item["customers_impacted"] for item in incidents)
    site_totals = defaultdict(int)
    for item in incidents:
        site_totals[item["site"]] += item["customers_impacted"]
    most_impacted_site = max(site_totals.items(), key=lambda pair: (pair[1], pair[0]))[0]
    highest_severity = min(incidents, key=lambda item: SEVERITY_RANK[item["severity"]])["severity"]
    severity_counts = Counter(item["severity"] for item in incidents)
    return {
        "total_incidents": len(incidents),
        "open_incidents": len(open_incidents),
        "resolved_incidents": len(resolved_incidents),
        "highest_severity": highest_severity,
        "total_customers": total_customers,
        "most_impacted_site": most_impacted_site,
        "severity_counts": severity_counts,
    }


def sorted_incidents(incidents):
    return sorted(incidents, key=lambda item: (SEVERITY_RANK[item["severity"]], item["started_at"]))


def top_impacted_incidents(incidents, limit=3):
    return sorted(
        incidents,
        key=lambda item: (-item["customers_impacted"], SEVERITY_RANK[item["severity"]], item["started_at"]),
    )[:limit]


def build_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=28,
            textColor=colors.HexColor("#173F5F"),
            spaceAfter=16,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            textColor=colors.HexColor("#0B3954"),
            spaceBefore=6,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Body",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SmallBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Stat",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=12,
            textColor=colors.HexColor("#102A43"),
        )
    )
    return styles


def summary_table(metrics, styles):
    cells = [
        Paragraph(f"<b>Total Incidents:</b> {metrics['total_incidents']}", styles["Stat"]),
        Paragraph(f"<b>Open Incidents:</b> {metrics['open_incidents']}", styles["Stat"]),
        Paragraph(f"<b>Resolved Incidents:</b> {metrics['resolved_incidents']}", styles["Stat"]),
        Paragraph(f"<b>Highest Severity:</b> {metrics['highest_severity']}", styles["Stat"]),
        Paragraph(f"<b>Total Customers Impacted:</b> {metrics['total_customers']}", styles["Stat"]),
        Paragraph(f"<b>Most Impacted Site:</b> {metrics['most_impacted_site']}", styles["Stat"]),
    ]
    table = Table([[cells[0], cells[1]], [cells[2], cells[3]], [cells[4], cells[5]]], colWidths=[3.7 * inch, 3.7 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EAF4F4")),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#4F6D7A")),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#A9BCD0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def incident_log_table(incidents, styles):
    header = [
        "Incident ID",
        "Title",
        "Site",
        "Severity",
        "Status",
        "Owner",
        "Started",
        "Duration (min)",
        "Impacted Customers",
        "Next Update",
    ]
    rows = [header]
    for incident in incidents:
        rows.append(
            [
                Paragraph(incident["incident_id"], styles["SmallBody"]),
                Paragraph(incident["title"], styles["SmallBody"]),
                Paragraph(incident["site"], styles["SmallBody"]),
                Paragraph(incident["severity"], styles["SmallBody"]),
                Paragraph(incident["status"], styles["SmallBody"]),
                Paragraph(incident["owner"], styles["SmallBody"]),
                Paragraph(incident["started_at"], styles["SmallBody"]),
                Paragraph(str(incident["duration_minutes"]), styles["SmallBody"]),
                Paragraph(str(incident["customers_impacted"]), styles["SmallBody"]),
                Paragraph(incident["next_update"], styles["SmallBody"]),
            ]
        )
    table = LongTable(
        rows,
        repeatRows=1,
        colWidths=[0.8 * inch, 1.8 * inch, 0.85 * inch, 0.65 * inch, 0.75 * inch, 0.85 * inch, 1.05 * inch, 0.75 * inch, 0.95 * inch, 1.55 * inch],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#173F5F")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F9FBFD")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F9FBFD"), colors.HexColor("#EEF4F8")]),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#7D8C99")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def add_page_chrome(canvas, doc):
    canvas.saveState()
    canvas.setTitle("Incident Briefing Report")
    canvas.setAuthor("Operations Intelligence Unit")
    canvas.setSubject("Leadership incident briefing")
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.HexColor("#4F5D75"))
    canvas.drawString(doc.leftMargin, doc.height + doc.topMargin + 10, "Incident Briefing Report")
    canvas.drawRightString(
        doc.pagesize[0] - doc.rightMargin,
        doc.bottomMargin - 12,
        f"Page {doc.page}",
    )
    canvas.restoreState()


def build_report():
    payload = load_data()
    briefing = payload["briefing"]
    incidents = payload["incidents"]
    actions = payload["leadership_actions"]
    metrics = compute_metrics(incidents)
    ordered_incidents = sorted_incidents(incidents)
    highlight_incidents = top_impacted_incidents(incidents)
    styles = build_styles()

    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=landscape(letter),
        leftMargin=36,
        rightMargin=36,
        topMargin=42,
        bottomMargin=34,
    )

    story = [
        Paragraph(briefing["title"], styles["ReportTitle"]),
        Paragraph(f"<b>Briefing Date:</b> {briefing['briefing_date']}", styles["Body"]),
        Paragraph(f"<b>Reporting Window:</b> {briefing['reporting_window']}", styles["Body"]),
        Paragraph(f"<b>Prepared For:</b> {briefing['prepared_for']}", styles["Body"]),
        Paragraph(f"<b>Prepared By:</b> {briefing['prepared_by']}", styles["Body"]),
        Paragraph(f"<b>Command Contact:</b> {briefing['command_contact']}", styles["Body"]),
        Spacer(1, 10),
        Paragraph("Executive Summary", styles["SectionHeading"]),
        summary_table(metrics, styles),
        Spacer(1, 12),
        Paragraph(
            (
                f"Severity mix: SEV-1={metrics['severity_counts'].get('SEV-1', 0)}, "
                f"SEV-2={metrics['severity_counts'].get('SEV-2', 0)}, "
                f"SEV-3={metrics['severity_counts'].get('SEV-3', 0)}."
            ),
            styles["Body"],
        ),
        Paragraph(
            "This briefing is intended for leadership review and prioritizes active risk, customer impact, and required executive support.",
            styles["Body"],
        ),
        PageBreak(),
        Paragraph("Leadership Actions", styles["SectionHeading"]),
        ListFlowable(
            [
                ListItem(Paragraph(action, styles["Body"]), value=index)
                for index, action in enumerate(actions, start=1)
            ],
            bulletType="1",
            leftIndent=18,
        ),
        Spacer(1, 12),
        Paragraph("Incident Highlights", styles["SectionHeading"]),
    ]

    for incident in highlight_incidents:
        story.append(
            Paragraph(
                (
                    f"<b>{incident['incident_id']} - {incident['title']}</b><br/>"
                    f"Site: {incident['site']} | Severity: {incident['severity']} | Status: {incident['status']} | "
                    f"Owner: {incident['owner']} | Impacted Customers: {incident['customers_impacted']}<br/>"
                    f"Summary: {incident['summary']}<br/>"
                    f"Next Update: {incident['next_update']}"
                ),
                styles["Body"],
            )
        )
        story.append(Spacer(1, 8))

    story.extend(
        [
            PageBreak(),
            Paragraph("Detailed Incident Log", styles["SectionHeading"]),
            incident_log_table(ordered_incidents, styles),
        ]
    )

    doc.build(story, onFirstPage=add_page_chrome, onLaterPages=add_page_chrome)


if __name__ == "__main__":
    build_report()
PY

python3 /tmp/generate_incident_briefing.py
