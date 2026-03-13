#!/usr/bin/env python3
from pathlib import Path
import sys

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


PAGE_WIDTH, PAGE_HEIGHT = letter
LEFT = 0.65 * inch
RIGHT = PAGE_WIDTH - LEFT
TOP = PAGE_HEIGHT - 0.6 * inch
FIELD_HEIGHT = 18
TEXT = HexColor("#111111")
ACCENT = HexColor("#17324D")


def header(c: canvas.Canvas, title: str, page_no: int) -> None:
    c.setFont("Helvetica-Bold", 15)
    c.setFillColor(ACCENT)
    c.drawString(LEFT, TOP, "APP-003 Appellant's Notice Designating Record on Appeal")
    c.setFillColor(TEXT)
    c.setFont("Helvetica", 9)
    c.drawRightString(RIGHT, TOP + 2, f"Training Form - Page {page_no} of 3")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(LEFT, TOP - 0.28 * inch, title)
    c.setLineWidth(0.8)
    c.line(LEFT, TOP - 0.34 * inch, RIGHT, TOP - 0.34 * inch)


def text_field(
    c: canvas.Canvas,
    name: str,
    x: float,
    y: float,
    width: float,
    height: float = FIELD_HEIGHT,
) -> None:
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
    header(c, "Appellant, Trial Court, and Record Method", 1)
    y = TOP - 0.58 * inch

    c.setFont("Helvetica", 9.5)
    c.drawString(LEFT, y, "Complete the appellant contact information, the superior court caption, and the record selection.")
    y -= 0.3 * inch

    c.setFont("Helvetica-Bold", 11)
    c.drawString(LEFT, y, "1. Appellant Information")
    y -= 0.28 * inch
    c.setFont("Helvetica", 10)
    c.drawString(LEFT, y, "Name")
    text_field(c, "appellant.name", LEFT + 0.78 * inch, y - 8, 2.7 * inch)
    c.drawString(LEFT + 3.9 * inch, y, "Phone")
    text_field(c, "appellant.phone", LEFT + 4.45 * inch, y - 8, 1.6 * inch)
    y -= 0.42 * inch
    c.drawString(LEFT, y, "Street address")
    text_field(c, "appellant.street", LEFT + 1.02 * inch, y - 8, 5.03 * inch)
    y -= 0.42 * inch
    c.drawString(LEFT, y, "City")
    text_field(c, "appellant.city", LEFT + 0.78 * inch, y - 8, 2.05 * inch)
    c.drawString(LEFT + 3.15 * inch, y, "State")
    text_field(c, "appellant.state", LEFT + 3.62 * inch, y - 8, 0.7 * inch)
    c.drawString(LEFT + 4.65 * inch, y, "ZIP")
    text_field(c, "appellant.zip", LEFT + 4.95 * inch, y - 8, 1.1 * inch)
    y -= 0.42 * inch
    c.drawString(LEFT, y, "Email")
    text_field(c, "appellant.email", LEFT + 0.78 * inch, y - 8, 5.27 * inch)

    y -= 0.58 * inch
    c.setFont("Helvetica-Bold", 11)
    c.drawString(LEFT, y, "2. Superior Court Caption")
    y -= 0.28 * inch
    c.setFont("Helvetica", 10)
    c.drawString(LEFT, y, "Court")
    text_field(c, "court.name", LEFT + 0.78 * inch, y - 8, 5.27 * inch)
    y -= 0.42 * inch
    c.drawString(LEFT, y, "Branch")
    text_field(c, "court.branch", LEFT + 0.78 * inch, y - 8, 5.27 * inch)
    y -= 0.42 * inch
    c.drawString(LEFT, y, "Street")
    text_field(c, "court.street", LEFT + 0.78 * inch, y - 8, 5.27 * inch)
    y -= 0.42 * inch
    c.drawString(LEFT, y, "City, ZIP")
    text_field(c, "court.city_zip", LEFT + 0.78 * inch, y - 8, 2.35 * inch)
    c.drawString(LEFT + 3.55 * inch, y, "Appeal case no. (leave blank)")
    text_field(c, "appeal.case_number", LEFT + 5.25 * inch, y - 8, 0.8 * inch)
    y -= 0.42 * inch
    c.drawString(LEFT, y, "Plaintiff / appellant")
    text_field(c, "case.plaintiff", LEFT + 1.22 * inch, y - 8, 2.65 * inch)
    c.drawString(LEFT + 4.2 * inch, y, "Case no.")
    text_field(c, "case.number", LEFT + 4.78 * inch, y - 8, 1.27 * inch)
    y -= 0.42 * inch
    c.drawString(LEFT, y, "Defendant / respondent")
    text_field(c, "case.defendant", LEFT + 1.42 * inch, y - 8, 4.63 * inch)
    y -= 0.42 * inch
    c.drawString(LEFT, y, "Notice of appeal filed")
    text_field(c, "notice.date_filed", LEFT + 1.3 * inch, y - 8, 1.2 * inch)

    y -= 0.56 * inch
    c.setFont("Helvetica-Bold", 11)
    c.drawString(LEFT, y, "3. Record on Appeal")
    y -= 0.24 * inch
    c.setFont("Helvetica", 10)
    options = [
        ("record.clerk_transcript", "Clerk's transcript"),
        ("record.appendix", "Appendix"),
        ("record.agreed_statement", "Agreed statement"),
        ("record.settled_statement", "Settled statement"),
    ]
    for name, label in options:
        checkbox_field(c, name, LEFT, y - 3)
        c.drawString(LEFT + 0.22 * inch, y, label)
        y -= 0.3 * inch

    y -= 0.02 * inch
    c.setFont("Helvetica-Bold", 10)
    c.drawString(LEFT, y, "Reserved for clerk (leave blank)")
    y -= 0.22 * inch
    c.setFont("Helvetica", 10)
    text_field(c, "court.clerk_notes", LEFT, y - 40, 6.05 * inch, 34)


def page_two(c: canvas.Canvas) -> None:
    header(c, "Clerk's Transcript Designation", 2)
    y = TOP - 0.58 * inch

    c.setFont("Helvetica", 9.5)
    c.drawString(LEFT, y, "List each document to include in the clerk's transcript and the filing date.")
    y -= 0.34 * inch

    c.setFont("Helvetica-Bold", 10)
    c.drawString(LEFT, y, "Document")
    c.drawString(LEFT + 4.95 * inch, y, "Filed date")
    y -= 0.12 * inch
    c.line(LEFT, y, RIGHT, y)
    y -= 0.22 * inch

    c.setFont("Helvetica", 10)
    for idx in range(1, 8):
        c.drawString(LEFT, y + 4, f"{idx}.")
        text_field(c, f"clerk.doc{idx}.title", LEFT + 0.2 * inch, y - 8, 4.55 * inch)
        text_field(c, f"clerk.doc{idx}.date", LEFT + 4.95 * inch, y - 8, 1.1 * inch)
        y -= 0.38 * inch

    c.setFont("Helvetica-Bold", 10)
    c.drawString(LEFT, y, "Additional document notes (leave blank unless needed)")
    y -= 0.22 * inch
    c.setFont("Helvetica", 10)
    text_field(c, "clerk.additional_notes", LEFT, y - 40, 6.05 * inch, 34)


def page_three(c: canvas.Canvas) -> None:
    header(c, "Reporter's Transcript and Signature", 3)
    y = TOP - 0.58 * inch

    c.setFont("Helvetica-Bold", 11)
    c.drawString(LEFT, y, "4. Reporter's Transcript")
    y -= 0.26 * inch
    c.setFont("Helvetica", 10)
    reporter_options = [
        ("reporter.transcript_requested", "Request a reporter's transcript"),
        ("reporter.no_reporter_transcript", "No reporter's transcript will be prepared"),
        ("reporter.all_proceedings", "Designate all proceedings"),
        ("reporter.selected_proceedings", "Designate only selected proceedings"),
        ("reporter.pay_estimated_cost", "Appellant will pay the estimated transcript cost"),
        ("reporter.fee_waiver", "Appellant has a fee waiver"),
    ]
    for name, label in reporter_options:
        checkbox_field(c, name, LEFT, y - 3)
        c.drawString(LEFT + 0.22 * inch, y, label)
        y -= 0.3 * inch

    y -= 0.08 * inch
    c.setFont("Helvetica-Bold", 10)
    c.drawString(LEFT, y, "Selected oral proceedings")
    y -= 0.2 * inch
    c.setFont("Helvetica", 9)
    c.drawString(LEFT, y, "Date")
    c.drawString(LEFT + 1.2 * inch, y, "Description")
    c.drawString(LEFT + 4.55 * inch, y, "Dept.")
    c.drawString(LEFT + 5.18 * inch, y, "Reporter")
    y -= 0.12 * inch
    c.line(LEFT, y, RIGHT, y)
    y -= 0.22 * inch

    c.setFont("Helvetica", 10)
    for idx in range(1, 4):
        text_field(c, f"hearing.{idx}.date", LEFT, y - 8, 1.0 * inch)
        text_field(c, f"hearing.{idx}.description", LEFT + 1.2 * inch, y - 8, 3.1 * inch)
        text_field(c, f"hearing.{idx}.department", LEFT + 4.55 * inch, y - 8, 0.45 * inch)
        text_field(c, f"hearing.{idx}.reporter", LEFT + 5.18 * inch, y - 8, 0.87 * inch)
        y -= 0.4 * inch

    c.setFont("Helvetica-Bold", 10)
    c.drawString(LEFT, y, "Reporter notes (leave blank unless needed)")
    y -= 0.22 * inch
    c.setFont("Helvetica", 10)
    text_field(c, "reporter.notes", LEFT, y - 34, 6.05 * inch, 28)

    y -= 0.76 * inch
    c.setFont("Helvetica-Bold", 11)
    c.drawString(LEFT, y, "5. Signature")
    y -= 0.28 * inch
    c.setFont("Helvetica", 10)
    c.drawString(LEFT, y, "Signature name")
    text_field(c, "signature.name", LEFT + 1.02 * inch, y - 8, 2.4 * inch)
    c.drawString(LEFT + 3.85 * inch, y, "Date")
    text_field(c, "signature.date", LEFT + 4.2 * inch, y - 8, 1.1 * inch)
    y -= 0.44 * inch
    c.drawString(LEFT, y, "Proof of service name (leave blank)")
    text_field(c, "service.name", LEFT + 1.85 * inch, y - 8, 1.55 * inch)
    c.drawString(LEFT + 3.85 * inch, y, "Service date")
    text_field(c, "service.date", LEFT + 4.65 * inch, y - 8, 1.4 * inch)


def build_pdf(output_path: Path) -> None:
    c = canvas.Canvas(str(output_path), pagesize=letter)
    c.setTitle("APP-003 Blank")
    c.setAuthor("OpenAI Codex")
    c.setSubject("Blank appellate record designation training form")

    page_one(c)
    c.showPage()
    page_two(c)
    c.showPage()
    page_three(c)
    c.save()


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: create_app003_blank.py OUTPUT_PDF")
        return 1
    output_path = Path(sys.argv[1])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    build_pdf(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
