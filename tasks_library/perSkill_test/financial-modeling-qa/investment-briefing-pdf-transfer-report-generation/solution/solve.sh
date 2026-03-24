#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import csv
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path("/root")
HOLDINGS_PATH = ROOT / "portfolio_holdings.csv"
ATTRIBUTION_PATH = ROOT / "performance_attribution.csv"
RISK_PATH = ROOT / "risk_notes.json"
OUTPUT_PATH = ROOT / "investment_committee_briefing.pdf"


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


holdings = load_csv(HOLDINGS_PATH)
attribution = load_csv(ATTRIBUTION_PATH)
with RISK_PATH.open("r", encoding="utf-8") as f:
    risk = json.load(f)

sorted_holdings = sorted(holdings, key=lambda row: float(row["WeightPct"]), reverse=True)
top_holding = sorted_holdings[0]
top_five_weight = sum(float(row["WeightPct"]) for row in sorted_holdings[:5])
best_sleeve = max(attribution, key=lambda row: float(row["ContributionBps"]))
worst_sleeve = min(attribution, key=lambda row: float(row["ContributionBps"]))
active_return_bps = round((risk["portfolio_return_pct"] - risk["benchmark_return_pct"]) * 100)

summary_text = (
    f"{risk['portfolio_name']} returned {risk['portfolio_return_pct']:.2f}% in {risk['report_period']}, "
    f"ahead of the {risk['benchmark_name']} by {active_return_bps} bps. "
    f"The top holding was {top_holding['Ticker']} at {float(top_holding['WeightPct']):.1f}% of capital, "
    f"and the top five holdings represented {top_five_weight:.1f}% of the portfolio. "
    f"{best_sleeve['Sleeve']} was the strongest attribution sleeve at {int(float(best_sleeve['ContributionBps']))} bps, "
    f"while {worst_sleeve['Sleeve']} was the weakest at {int(float(worst_sleeve['ContributionBps']))} bps. "
    f"Risk posture remains constructive with net exposure at {risk['net_exposure_pct']}%, gross exposure at {risk['gross_exposure_pct']}%, "
    f"tracking error at {risk['tracking_error_pct']:.1f}%, and five-day liquidity at {risk['liquidity_within_5_days_pct']}%."
)

doc = SimpleDocTemplate(
    str(OUTPUT_PATH),
    pagesize=letter,
    leftMargin=0.75 * inch,
    rightMargin=0.75 * inch,
    topMargin=0.75 * inch,
    bottomMargin=0.75 * inch,
)

styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="BriefingTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#153B50"),
    )
)
styles.add(
    ParagraphStyle(
        name="SectionHeading",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#153B50"),
        spaceAfter=12,
    )
)
styles.add(
    ParagraphStyle(
        name="Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=11,
        leading=16,
        alignment=TA_LEFT,
        spaceAfter=10,
    )
)
styles.add(
    ParagraphStyle(
        name="RiskItem",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=15,
        spaceAfter=10,
    )
)

story = []

story.append(Spacer(1, 1.7 * inch))
story.append(Paragraph("Investment Committee Briefing", styles["BriefingTitle"]))
story.append(Spacer(1, 0.35 * inch))
story.append(Paragraph(risk["portfolio_name"], styles["Heading2"]))
story.append(Spacer(1, 0.1 * inch))
story.append(Paragraph(f"Report Period: {risk['report_period']}", styles["Body"]))
story.append(Paragraph(f"Committee Meeting Date: {risk['committee_meeting_date']}", styles["Body"]))
story.append(PageBreak())

story.append(Paragraph("Executive Summary", styles["SectionHeading"]))
story.append(Paragraph(summary_text, styles["Body"]))
story.append(PageBreak())

story.append(Paragraph("Performance Attribution", styles["SectionHeading"]))
table_rows = [[
    "Sleeve",
    "Portfolio Return (%)",
    "Benchmark Return (%)",
    "Contribution (bps)",
]]
for row in attribution:
    table_rows.append([
        row["Sleeve"],
        f"{float(row['PortfolioReturnPct']):.1f}",
        f"{float(row['BenchmarkReturnPct']):.1f}",
        f"{int(float(row['ContributionBps']))}",
    ])

performance_table = Table(table_rows, colWidths=[2.4 * inch, 1.5 * inch, 1.5 * inch, 1.4 * inch])
performance_table.setStyle(
    TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#153B50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("LEADING", (0, 0), (-1, -1), 12),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F5F7FA"), colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#AAB7C4")),
            ("ALIGN", (1, 1), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
        ]
    )
)
story.append(performance_table)
story.append(PageBreak())

story.append(Paragraph("Risk Watchlist", styles["SectionHeading"]))
for idx, item in enumerate(risk["risk_items"], start=1):
    text = (
        f"{idx}. {item['title']}<br/>"
        f"Severity: {item['severity']}<br/>"
        f"Owner: {item['owner']}<br/>"
        f"Mitigation: {item['mitigation']}"
    )
    story.append(Paragraph(text, styles["RiskItem"]))

story.append(Spacer(1, 0.2 * inch))
story.append(Paragraph(f"Escalation Note: {risk['escalation_note']}", styles["Body"]))

doc.build(story)
PY
