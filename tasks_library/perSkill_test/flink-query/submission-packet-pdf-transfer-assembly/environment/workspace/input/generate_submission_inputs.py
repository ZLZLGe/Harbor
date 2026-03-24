import json
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


INPUT_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = INPUT_DIR / "submission_manifest.json"


def draw_lines(pdf_path, title, lines):
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    width, height = letter
    c.setTitle(title)

    for index, page_lines in enumerate(lines):
        y = height - 72
        c.setFont("Helvetica-Bold", 18)
        c.drawString(72, y, page_lines[0])
        y -= 28
        c.setFont("Helvetica", 11)
        for line in page_lines[1:]:
            c.drawString(72, y, line)
            y -= 18
        c.setFont("Helvetica-Oblique", 10)
        c.drawString(72, 40, f"Source page {index + 1}")
        c.showPage()

    c.save()


def apply_rotations(pdf_path, rotations):
    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()

    for page_index, page in enumerate(reader.pages, start=1):
        rotation = rotations.get(page_index, 0)
        if rotation:
            page.rotate(rotation)
        writer.add_page(page)

    with pdf_path.open("wb") as handle:
        writer.write(handle)


def build_inputs():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    inspection_pdf = INPUT_DIR / "inspection_summary.pdf"
    monitoring_pdf = INPUT_DIR / "effluent_monitoring.pdf"
    training_pdf = INPUT_DIR / "training_records.pdf"

    draw_lines(
        inspection_pdf,
        "Inspection Summary Packet",
        [
            [
                "Inspection Summary - Transmittal Letter",
                "Marker: INSPECT-LETTER",
                "This cover letter is not part of the final submission packet.",
                "Routing note: internal review only.",
            ],
            [
                "Exhibit A - Inspection findings overview",
                "Marker: INSPECT-OVERVIEW",
                "Inspection date: 2026-03-04",
                "Overall status: open items remain under active remediation.",
            ],
            [
                "Exhibit B - Corrective action timeline",
                "Marker: CORRECTIVE-TIMELINE",
                "Milestone 1: neutralization sump cleaning completed.",
                "Milestone 2: secondary containment sealant scheduled for 2026-03-28.",
            ],
            [
                "Inspection Summary - Appendix Notes",
                "Marker: INSPECT-APPENDIX",
                "Historical appendix retained for reference only.",
                "Do not include this page in the assembled packet.",
            ],
        ],
    )
    apply_rotations(inspection_pdf, {3: 90})

    draw_lines(
        monitoring_pdf,
        "Effluent Monitoring Binder",
        [
            [
                "Exhibit C - March 2026 composite monitoring results",
                "Marker: MARCH-COMPOSITE",
                "Composite sample ID: M-2026-03",
                "Copper result: 0.41 mg/L",
                "Zinc result: 1.12 mg/L",
            ],
            [
                "Exhibit D - Quarterly trend exceptions summary",
                "Marker: TREND-EXCEPTIONS",
                "Exception window: 2026 Q1",
                "Observed spike on 2026-02-18 remained below escalation trigger.",
            ],
            [
                "Effluent Monitoring - Internal routing slip",
                "Marker: MONITORING-ROUTING",
                "This routing sheet is administrative only and must stay out of the packet.",
            ],
        ],
    )
    apply_rotations(monitoring_pdf, {2: 270})

    draw_lines(
        training_pdf,
        "Training Records Packet",
        [
            [
                "Training Records - Attendance ledger",
                "Marker: TRAINING-LEDGER",
                "Roster summary for archive use only.",
            ],
            [
                "Exhibit E - Hazmat refresher certificate",
                "Marker: HAZMAT-CERT",
                f"Prepared for applicant: {manifest['applicant']}",
                "Course completion date: 2026-02-11",
            ],
            [
                "Exhibit F - Spill drill sign-off",
                "Marker: SPILL-DRILL",
                "Drill date: 2026-02-25",
                "Shift lead signature recorded and approved.",
            ],
        ],
    )


if __name__ == "__main__":
    build_inputs()
