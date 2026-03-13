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
TOP = PAGE_HEIGHT - 0.65 * inch
FIELD_HEIGHT = 18
MULTILINE_FLAG = 1 << 12
TEXT = HexColor("#111111")
ACCENT = HexColor("#0F4C5C")


def header(c: canvas.Canvas, title: str, page_no: int) -> None:
    c.setFont("Helvetica-Bold", 15)
    c.setFillColor(ACCENT)
    c.drawString(LEFT, TOP, "UD-105 Answer - Unlawful Detainer (Training Form)")
    c.setFillColor(TEXT)
    c.setFont("Helvetica", 9)
    c.drawRightString(RIGHT, TOP + 2, f"Page {page_no} of 4")
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
    header(c, "Party Without Attorney and Court Caption", 1)
    y = TOP - 0.58 * inch
    c.setFont("Helvetica", 9.5)
    c.drawString(LEFT, y, "Complete the self-represented party information and the caption. Leave court hearing details blank.")
    y -= 0.28 * inch

    c.setFont("Helvetica-Bold", 11)
    c.drawString(LEFT, y, "1. Party Without Attorney")
    y -= 0.28 * inch
    c.setFont("Helvetica", 10)
    c.drawString(LEFT, y, "Name")
    text_field(c, "party.name", LEFT + 0.72 * inch, y - 8, 2.5 * inch)
    c.drawString(LEFT + 3.6 * inch, y, "Bar number")
    text_field(c, "party.bar_number", LEFT + 4.45 * inch, y - 8, 1.55 * inch)
    y -= 0.42 * inch
    c.drawString(LEFT, y, "Street address")
    text_field(c, "party.street", LEFT + 1.12 * inch, y - 8, 4.88 * inch)
    y -= 0.42 * inch
    c.drawString(LEFT, y, "City, state, ZIP")
    text_field(c, "party.city_state_zip", LEFT + 1.18 * inch, y - 8, 2.6 * inch)
    c.drawString(LEFT + 4.1 * inch, y, "Phone")
    text_field(c, "party.phone", LEFT + 4.65 * inch, y - 8, 1.35 * inch)
    y -= 0.42 * inch
    c.drawString(LEFT, y, "Email")
    text_field(c, "party.email", LEFT + 0.72 * inch, y - 8, 5.28 * inch)

    y -= 0.62 * inch
    c.setFont("Helvetica-Bold", 11)
    c.drawString(LEFT, y, "2. Court Caption")
    y -= 0.28 * inch
    c.setFont("Helvetica", 10)
    c.drawString(LEFT, y, "Court")
    text_field(c, "court.name", LEFT + 0.8 * inch, y - 8, 5.2 * inch)
    y -= 0.42 * inch
    c.drawString(LEFT, y, "Courthouse")
    text_field(c, "court.location", LEFT + 0.95 * inch, y - 8, 5.05 * inch)
    y -= 0.42 * inch
    c.drawString(LEFT, y, "Court address")
    text_field(c, "court.address", LEFT + 1.05 * inch, y - 8, 4.95 * inch)
    y -= 0.42 * inch
    c.drawString(LEFT, y, "Plaintiff")
    text_field(c, "caption.plaintiff", LEFT + 0.82 * inch, y - 8, 3.0 * inch)
    c.drawString(LEFT + 4.2 * inch, y, "Case number")
    text_field(c, "caption.case_number", LEFT + 5.0 * inch, y - 8, 1.0 * inch)
    y -= 0.42 * inch
    c.drawString(LEFT, y, "Defendant")
    text_field(c, "caption.defendant", LEFT + 0.86 * inch, y - 8, 3.0 * inch)
    y -= 0.62 * inch

    c.setFont("Helvetica-Bold", 11)
    c.drawString(LEFT, y, "3. Court Use Only (leave blank)")
    y -= 0.28 * inch
    c.setFont("Helvetica", 10)
    c.drawString(LEFT, y, "Hearing date")
    text_field(c, "court.hearing_date", LEFT + 0.98 * inch, y - 8, 1.45 * inch)
    c.drawString(LEFT + 2.8 * inch, y, "Department")
    text_field(c, "court.department", LEFT + 3.62 * inch, y - 8, 1.0 * inch)
    c.drawString(LEFT + 4.95 * inch, y, "Clerk initials")
    text_field(c, "court.clerk_initials", LEFT + 5.75 * inch, y - 8, 0.25 * inch)


def page_two(c: canvas.Canvas) -> None:
    header(c, "General Denial and Brief Facts", 2)
    y = TOP - 0.6 * inch
    c.setFont("Helvetica", 10)
    c.drawString(LEFT, y, "4. Response to Complaint")
    y -= 0.26 * inch
    checkbox_field(c, "response.general_denial", LEFT, y - 3)
    c.drawString(LEFT + 0.22 * inch, y, "General denial of the complaint")
    y -= 0.4 * inch

    c.setFont("Helvetica-Bold", 10)
    c.drawString(LEFT, y, "5. Brief facts supporting the denial")
    y -= 0.2 * inch
    c.setFont("Helvetica", 10)
    text_field(c, "response.denial_facts", LEFT, y - 70, 6.0 * inch, 64, multiline=True)

    y -= 1.18 * inch
    c.setFont("Helvetica-Bold", 10)
    c.drawString(LEFT, y, "6. Other statements (leave blank unless needed)")
    y -= 0.2 * inch
    c.setFont("Helvetica", 10)
    text_field(c, "response.other_statements", LEFT, y - 54, 6.0 * inch, 48, multiline=True)


def page_three(c: canvas.Canvas) -> None:
    header(c, "Affirmative Defenses", 3)
    y = TOP - 0.58 * inch
    c.setFont("Helvetica", 9.5)
    c.drawString(LEFT, y, "Select each defense supported by the facts. Leave unsupported defenses unchecked.")
    y -= 0.34 * inch

    defenses = [
        ("defense.notice_defective", "The 3-day notice was defective."),
        ("defense.rent_accepted_after_notice", "Plaintiff accepted rent after serving the notice."),
        ("defense.habitability", "Breach of habitability / serious repair conditions."),
        ("defense.retaliation", "Retaliatory eviction."),
        ("defense.discrimination", "Discrimination."),
        ("defense.nuisance", "Plaintiff cannot prove nuisance or wrongful conduct."),
        ("defense.other", "Other defense."),
    ]

    c.setFont("Helvetica", 10)
    for name, label in defenses:
        checkbox_field(c, name, LEFT, y - 3)
        c.drawString(LEFT + 0.22 * inch, y, label)
        y -= 0.34 * inch

    y -= 0.12 * inch
    c.setFont("Helvetica-Bold", 10)
    c.drawString(LEFT, y, "Other defense details (leave blank if not used)")
    y -= 0.2 * inch
    c.setFont("Helvetica", 10)
    text_field(c, "defense.other_text", LEFT, y - 54, 6.0 * inch, 48, multiline=True)


def page_four(c: canvas.Canvas) -> None:
    header(c, "Requests and Signature", 4)
    y = TOP - 0.58 * inch
    c.setFont("Helvetica-Bold", 11)
    c.drawString(LEFT, y, "7. Requests")
    y -= 0.28 * inch
    c.setFont("Helvetica", 10)
    requests = [
        ("request.dismiss_complaint", "Dismiss the complaint."),
        ("request.costs", "Award court costs to defendant."),
        ("request.attorney_fees", "Award attorney fees to defendant."),
        ("request.jury_trial", "Request a jury trial."),
    ]
    for name, label in requests:
        checkbox_field(c, name, LEFT, y - 3)
        c.drawString(LEFT + 0.22 * inch, y, label)
        y -= 0.34 * inch

    y -= 0.12 * inch
    c.setFont("Helvetica-Bold", 10)
    c.drawString(LEFT, y, "Other relief (leave blank unless supported)")
    y -= 0.2 * inch
    c.setFont("Helvetica", 10)
    text_field(c, "request.other_relief", LEFT, y - 54, 6.0 * inch, 48, multiline=True)

    y -= 1.05 * inch
    c.setFont("Helvetica-Bold", 11)
    c.drawString(LEFT, y, "8. Signature")
    y -= 0.28 * inch
    c.setFont("Helvetica", 10)
    c.drawString(LEFT, y, "Name")
    text_field(c, "signature.name", LEFT + 0.72 * inch, y - 8, 2.4 * inch)
    c.drawString(LEFT + 3.55 * inch, y, "Date")
    text_field(c, "signature.date", LEFT + 3.98 * inch, y - 8, 1.6 * inch)
    y -= 0.42 * inch
    c.drawString(LEFT, y, "Interpreter (leave blank if not needed)")
    text_field(c, "signature.interpreter", LEFT + 2.15 * inch, y - 8, 3.85 * inch)


def build_pdf(output_path: Path) -> None:
    c = canvas.Canvas(str(output_path), pagesize=letter)
    c.setTitle("UD-105 Blank")
    c.setAuthor("OpenAI Codex")
    c.setSubject("Blank training form for unlawful detainer answer tasks")

    page_one(c)
    c.showPage()
    page_two(c)
    c.showPage()
    page_three(c)
    c.showPage()
    page_four(c)
    c.save()


if __name__ == "__main__":
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("ud105-blank.pdf")
    output.parent.mkdir(parents=True, exist_ok=True)
    build_pdf(output)
