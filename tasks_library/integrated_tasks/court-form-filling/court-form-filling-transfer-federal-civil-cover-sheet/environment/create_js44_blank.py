#!/usr/bin/env python3
from pathlib import Path
import sys

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


PAGE_WIDTH, PAGE_HEIGHT = letter
LEFT = 0.65 * inch
TOP = PAGE_HEIGHT - 0.7 * inch
TEXT = HexColor("#111111")
ACCENT = HexColor("#0F3B5F")
FIELD_HEIGHT = 18
MULTILINE_FLAG = 1 << 12


def header(c: canvas.Canvas, title: str, page_no: int) -> None:
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(ACCENT)
    c.drawString(LEFT, TOP, "JS-44 Civil Cover Sheet (Training Form)")
    c.setFillColor(TEXT)
    c.setFont("Helvetica", 9)
    c.drawRightString(PAGE_WIDTH - LEFT, TOP + 2, f"Page {page_no} of 2")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(LEFT, TOP - 0.25 * inch, title)
    c.setLineWidth(0.9)
    c.line(LEFT, TOP - 0.31 * inch, PAGE_WIDTH - LEFT, TOP - 0.31 * inch)


def text_field(
    c: canvas.Canvas,
    name: str,
    x: float,
    y: float,
    width: float,
    height: float = FIELD_HEIGHT,
    multiline: bool = False,
) -> None:
    flags = MULTILINE_FLAG if multiline else 0
    c.acroForm.textfield(
        name=name,
        tooltip=name,
        x=x,
        y=y,
        width=width,
        height=height,
        borderStyle="solid",
        borderWidth=1,
        forceBorder=True,
        fontName="Helvetica",
        fontSize=10,
        textColor=TEXT,
        borderColor=ACCENT,
        fillColor=None,
        fieldFlags=flags,
    )


def checkbox_field(c: canvas.Canvas, name: str, x: float, y: float, checked: bool = False) -> None:
    c.acroForm.checkbox(
        name=name,
        tooltip=name,
        x=x,
        y=y,
        size=12,
        borderWidth=1,
        borderColor=ACCENT,
        fillColor=None,
        textColor=TEXT,
        forceBorder=True,
        checked=checked,
        buttonStyle="check",
    )


def page_one(c: canvas.Canvas) -> None:
    header(c, "Caption, Jurisdiction, Origin, and Jury Demand", 1)
    y = TOP - 0.55 * inch

    c.setFont("Helvetica", 9.5)
    instructions = [
        "Complete only the party, jurisdiction, origin, cause-of-action, and jury-demand sections.",
        "Leave clerk, judge, case number, demand amount, and related-case sections blank unless the case summary gives that information.",
    ]
    for line in instructions:
        c.drawString(LEFT, y, line)
        y -= 14

    y -= 6
    c.setFont("Helvetica-Bold", 11)
    c.drawString(LEFT, y, "Court Use Only (leave blank)")
    y -= 18
    c.setFont("Helvetica", 10)
    c.drawString(LEFT, y + 4, "Case number")
    text_field(c, "court.case_number", LEFT + 1.0 * inch, y - 6, 1.7 * inch)
    c.drawString(LEFT + 3.1 * inch, y + 4, "Assigned judge")
    text_field(c, "court.judge", LEFT + 4.15 * inch, y - 6, 1.9 * inch)
    y -= 30
    c.drawString(LEFT, y + 4, "Receipt number")
    text_field(c, "court.receipt_number", LEFT + 1.0 * inch, y - 6, 1.7 * inch)
    c.drawString(LEFT + 3.1 * inch, y + 4, "Demand amount")
    text_field(c, "complaint.demand_amount", LEFT + 4.15 * inch, y - 6, 1.9 * inch)

    y -= 42
    c.setFont("Helvetica-Bold", 11)
    c.drawString(LEFT, y, "I. Parties")
    y -= 20
    c.setFont("Helvetica", 10)
    c.drawString(LEFT, y + 4, "Case title")
    text_field(c, "case.title", LEFT + 0.85 * inch, y - 6, 5.25 * inch)
    y -= 30
    c.drawString(LEFT, y + 4, "Plaintiff")
    text_field(c, "plaintiff.name", LEFT + 0.85 * inch, y - 6, 3.3 * inch)
    c.drawString(LEFT + 4.45 * inch, y + 4, "County")
    text_field(c, "plaintiff.county", LEFT + 5.0 * inch, y - 6, 1.1 * inch)
    y -= 30
    c.drawString(LEFT, y + 4, "Defendant")
    text_field(c, "defendant.name", LEFT + 0.85 * inch, y - 6, 3.3 * inch)
    c.drawString(LEFT + 4.45 * inch, y + 4, "County")
    text_field(c, "defendant.county", LEFT + 5.0 * inch, y - 6, 1.1 * inch)

    y -= 42
    c.setFont("Helvetica-Bold", 11)
    c.drawString(LEFT, y, "II. Basis of Jurisdiction")
    y -= 18
    c.setFont("Helvetica", 10)
    jurisdiction_options = [
        ("jurisdiction_us_plaintiff", "1 U.S. Government Plaintiff"),
        ("jurisdiction_us_defendant", "2 U.S. Government Defendant"),
        ("jurisdiction_federal_question", "3 Federal Question"),
        ("jurisdiction_diversity", "4 Diversity"),
    ]
    for name, label in jurisdiction_options:
        checkbox_field(c, name, LEFT, y - 3)
        c.drawString(LEFT + 18, y, label)
        y -= 18

    y -= 6
    c.setFont("Helvetica-Bold", 11)
    c.drawString(LEFT, y, "III. Origin")
    y -= 18
    c.setFont("Helvetica", 10)
    origin_options = [
        ("origin_original", "1 Original Proceeding"),
        ("origin_removed", "2 Removed from State Court"),
        ("origin_remanded", "3 Remanded from Appellate Court"),
        ("origin_reinstated", "4 Reinstated or Reopened"),
        ("origin_transferred", "5 Transferred from Another District"),
        ("origin_multidistrict", "6 Multidistrict Litigation"),
    ]
    for name, label in origin_options:
        checkbox_field(c, name, LEFT, y - 3)
        c.drawString(LEFT + 18, y, label)
        y -= 18

    y -= 8
    c.setFont("Helvetica-Bold", 11)
    c.drawString(LEFT, y, "IV. Cause of Action")
    y -= 18
    c.setFont("Helvetica", 10)
    c.drawString(LEFT, y + 4, "Statute")
    text_field(c, "cause.statute", LEFT + 0.65 * inch, y - 6, 1.45 * inch)
    c.drawString(LEFT + 2.45 * inch, y + 4, "Related case")
    text_field(c, "court.related_case", LEFT + 3.35 * inch, y - 6, 2.75 * inch)
    y -= 30
    c.drawString(LEFT, y + 4, "Short description")
    text_field(c, "cause.description", LEFT + 1.2 * inch, y - 6, 4.9 * inch, multiline=True, height=36)

    y -= 50
    c.setFont("Helvetica-Bold", 11)
    c.drawString(LEFT, y, "V. Jury Demand")
    y -= 18
    c.setFont("Helvetica", 10)
    checkbox_field(c, "jury_yes", LEFT, y - 3)
    c.drawString(LEFT + 18, y, "Yes")
    checkbox_field(c, "jury_no", LEFT + 0.9 * inch, y - 3)
    c.drawString(LEFT + 0.9 * inch + 18, y, "No")


def page_two(c: canvas.Canvas) -> None:
    header(c, "Nature of Suit", 2)
    y = TOP - 0.55 * inch

    c.setFont("Helvetica", 9.5)
    c.drawString(LEFT, y, "Select the single nature-of-suit category that best matches the case summary.")
    y -= 22

    categories = [
        ("nature_110_insurance", "110 Insurance"),
        ("nature_190_other_contract", "190 Other Contract"),
        ("nature_310_airplane", "310 Airplane"),
        ("nature_442_employment", "442 Civil Rights: Employment"),
        ("nature_710_flsa", "710 Fair Labor Standards Act"),
        ("nature_790_other_labor", "790 Other Labor Litigation"),
        ("nature_820_copyright", "820 Copyrights"),
        ("nature_840_trademark", "840 Trademark"),
    ]

    c.setFont("Helvetica", 10)
    for name, label in categories:
        checkbox_field(c, name, LEFT, y - 3)
        c.drawString(LEFT + 18, y, label)
        y -= 22

    y -= 8
    c.setFont("Helvetica-Bold", 11)
    c.drawString(LEFT, y, "Notes (leave blank unless the summary requires it)")
    y -= 20
    c.setFont("Helvetica", 10)
    text_field(c, "nature.notes", LEFT, y - 54, 6.05 * inch, height=50, multiline=True)


def build_pdf(output_path: Path) -> None:
    c = canvas.Canvas(str(output_path), pagesize=letter)
    c.setTitle("JS-44 Blank")
    c.setAuthor("OpenAI Codex")
    c.setSubject("Blank federal civil cover sheet training form")

    page_one(c)
    c.showPage()
    page_two(c)
    c.save()


if __name__ == "__main__":
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("js44-blank.pdf")
    output.parent.mkdir(parents=True, exist_ok=True)
    build_pdf(output)
